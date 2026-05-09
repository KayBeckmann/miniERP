from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.order import Order, TimeEntry
from app.schemas.order import (
    OrderCreate, OrderListResponse, OrderRead, OrderUpdate,
    TimeEntryCreate, TimeEntryRead, TimeEntryUpdate,
)
from app.services.number_sequence import next_number

router = APIRouter()


@router.get("", response_model=OrderListResponse)
async def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> OrderListResponse:
    q = select(Order).where(Order.tenant_id == tenant_id)
    if status_filter:
        q = q.where(Order.status == status_filter)
    if search:
        like = f"%{search}%"
        q = q.where(or_(Order.title.ilike(like), Order.order_no.ilike(like)))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    orders = (
        await db.execute(
            q.options(selectinload(Order.time_entries))
            .order_by(Order.created_at.desc()).offset(skip).limit(limit)
        )
    ).scalars().all()

    items = []
    for o in orders:
        data = OrderRead.model_validate(o)
        data.hours_total = float(sum(e.hours for e in o.time_entries))
        data.hours_billable = float(sum(e.hours for e in o.time_entries if e.billable))
        items.append(data)

    return OrderListResponse(items=items, total=total)


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: OrderCreate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> OrderRead:
    order_no = await next_number(db, tenant_id, "order")
    order = Order(**body.model_dump(), tenant_id=tenant_id, order_no=order_no)
    db.add(order)
    await db.commit()
    await db.refresh(order, ["time_entries"])
    data = OrderRead.model_validate(order)
    return data


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> OrderRead:
    order = await _get_or_404(db, order_id, tenant_id)
    data = OrderRead.model_validate(order)
    data.hours_total = float(sum(e.hours for e in order.time_entries))
    data.hours_billable = float(sum(e.hours for e in order.time_entries if e.billable))
    return data


@router.patch("/{order_id}", response_model=OrderRead)
async def update_order(
    order_id: int,
    body: OrderUpdate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> OrderRead:
    order = await _get_or_404(db, order_id, tenant_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(order, k, v)
    order.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(order, ["time_entries"])
    data = OrderRead.model_validate(order)
    data.hours_total = float(sum(e.hours for e in order.time_entries))
    data.hours_billable = float(sum(e.hours for e in order.time_entries if e.billable))
    return data


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> None:
    order = await _get_or_404(db, order_id, tenant_id)
    await db.delete(order)
    await db.commit()


# ── Time Entries ────────────────────────────────────────────────────────────

@router.get("/{order_id}/time", response_model=list[TimeEntryRead])
async def list_time_entries(
    order_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[TimeEntry]:
    await _get_or_404(db, order_id, tenant_id)
    result = await db.execute(
        select(TimeEntry).where(TimeEntry.order_id == order_id)
        .order_by(TimeEntry.entry_date.desc())
    )
    return result.scalars().all()


@router.post("/{order_id}/time", response_model=TimeEntryRead, status_code=status.HTTP_201_CREATED)
async def create_time_entry(
    order_id: int,
    body: TimeEntryCreate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
) -> TimeEntry:
    await _get_or_404(db, order_id, tenant_id)
    entry = TimeEntry(**body.model_dump(), order_id=order_id, user_id=user.id)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.patch("/{order_id}/time/{entry_id}", response_model=TimeEntryRead)
async def update_time_entry(
    order_id: int,
    entry_id: int,
    body: TimeEntryUpdate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> TimeEntry:
    await _get_or_404(db, order_id, tenant_id)
    entry = await _get_entry_or_404(db, entry_id, order_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(entry, k, v)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{order_id}/time/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_time_entry(
    order_id: int,
    entry_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> None:
    await _get_or_404(db, order_id, tenant_id)
    entry = await _get_entry_or_404(db, entry_id, order_id)
    await db.delete(entry)
    await db.commit()


async def _get_or_404(db: AsyncSession, order_id: int, tenant_id: int) -> Order:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.time_entries))
        .where(Order.id == order_id, Order.tenant_id == tenant_id)
    )
    order = result.scalars().first()
    if not order:
        raise HTTPException(404, "Auftrag nicht gefunden")
    return order


async def _get_entry_or_404(db: AsyncSession, entry_id: int, order_id: int) -> TimeEntry:
    result = await db.execute(
        select(TimeEntry).where(TimeEntry.id == entry_id, TimeEntry.order_id == order_id)
    )
    entry = result.scalars().first()
    if not entry:
        raise HTTPException(404, "Zeiteintrag nicht gefunden")
    return entry
