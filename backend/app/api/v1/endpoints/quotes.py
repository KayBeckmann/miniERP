from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.customer import Customer
from app.models.order import Order
from app.models.quote import PositionHistory, Quote, QuoteGroup, QuoteItem
from app.models.tenant import Tenant
from app.schemas.order import OrderRead
from app.schemas.quote import (
    ConvertToOrderBody,
    PositionHistoryRead,
    QuoteCreate,
    QuoteGroupIn,
    QuoteGroupRead,
    QuoteItemIn,
    QuoteItemRead,
    QuoteListResponse,
    QuoteRead,
    QuoteStatusUpdate,
    QuoteUpdate,
)
from app.services import calculation, number_sequence
from app.services import pdf as pdf_service

router = APIRouter()

_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["sent", "expired"],
    "sent": ["accepted", "declined", "expired"],
    "accepted": ["draft"],
    "declined": [],
    "expired": [],
}


@router.get("/position-history", response_model=list[PositionHistoryRead])
async def list_position_history(
    search: str | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[PositionHistory]:
    q = select(PositionHistory).where(PositionHistory.tenant_id == tenant_id)
    if search:
        q = q.where(PositionHistory.description.ilike(f"%{search}%"))
    q = q.order_by(PositionHistory.usage_count.desc(), PositionHistory.last_used_at.desc()).limit(limit)
    return (await db.execute(q)).scalars().all()


@router.get("", response_model=QuoteListResponse)
async def list_quotes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> QuoteListResponse:
    q = (
        select(Quote)
        .options(selectinload(Quote.all_items), selectinload(Quote.groups).selectinload(QuoteGroup.items))
        .where(Quote.tenant_id == tenant_id)
    )
    if status_filter:
        q = q.where(Quote.status == status_filter)
    if search:
        like = f"%{search}%"
        q = q.join(Customer, Quote.customer_id == Customer.id).where(
            or_(Quote.quote_no.ilike(like), Customer.name.ilike(like))
        )
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    quotes = (await db.execute(q.order_by(Quote.date.desc()).offset(skip).limit(limit))).scalars().all()
    return QuoteListResponse(items=[_to_read(qt) for qt in quotes], total=total)


@router.post("", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
async def create_quote(
    body: QuoteCreate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> QuoteRead:
    await _assert_customer(db, body.customer_id, tenant_id)
    quote_no = await number_sequence.next_number(db, tenant_id, "quote")
    quote = Quote(
        tenant_id=tenant_id, customer_id=body.customer_id, quote_no=quote_no,
        date=body.quote_date, valid_until=body.valid_until,
        notes=body.notes, internal_notes=body.internal_notes,
    )
    db.add(quote)
    await db.flush()
    all_items = await _create_items(db, quote.id, body.groups, body.items)
    quote.subtotal, quote.vat_total, quote.total = calculation.calc_totals(all_items)
    await db.commit()
    await _update_position_history(db, tenant_id, all_items)
    return await _load_quote(db, quote.id)


@router.get("/{quote_id}", response_model=QuoteRead)
async def get_quote(
    quote_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> QuoteRead:
    return await _load_quote(db, quote_id, tenant_id)


@router.patch("/{quote_id}", response_model=QuoteRead)
async def update_quote(
    quote_id: int,
    body: QuoteUpdate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> QuoteRead:
    quote = await _get_raw_or_404(db, quote_id, tenant_id)
    if quote.status != "draft":
        raise HTTPException(400, "Nur Entwürfe können bearbeitet werden.")
    for attr, field in [("customer_id", "customer_id"), ("date", "quote_date"),
                         ("valid_until", "valid_until"), ("notes", "notes"),
                         ("internal_notes", "internal_notes")]:
        value = getattr(body, field, None)
        if value is not None:
            setattr(quote, attr, value)
    if body.groups is not None or body.items is not None:
        for item in (await db.execute(select(QuoteItem).where(QuoteItem.quote_id == quote.id))).scalars():
            await db.delete(item)
        for grp in (await db.execute(select(QuoteGroup).where(QuoteGroup.quote_id == quote.id))).scalars():
            await db.delete(grp)
        await db.flush()
        all_items = await _create_items(db, quote.id, body.groups or [], body.items or [])
        quote.subtotal, quote.vat_total, quote.total = calculation.calc_totals(all_items)
        await _update_position_history(db, tenant_id, all_items)
    quote.updated_at = datetime.now(timezone.utc)
    quote.version += 1
    await db.commit()
    return await _load_quote(db, quote.id)


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(
    quote_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> None:
    quote = await _get_raw_or_404(db, quote_id, tenant_id)
    if quote.status != "draft":
        raise HTTPException(400, "Nur Entwürfe können gelöscht werden.")
    await db.delete(quote)
    await db.commit()


@router.patch("/{quote_id}/status", response_model=QuoteRead)
async def update_status(
    quote_id: int,
    body: QuoteStatusUpdate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> QuoteRead:
    quote = await _get_raw_or_404(db, quote_id, tenant_id)
    allowed = _TRANSITIONS.get(quote.status, [])
    if body.status not in allowed:
        raise HTTPException(400, f"Übergang '{quote.status}' → '{body.status}' nicht erlaubt.")
    quote.status = body.status
    quote.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return await _load_quote(db, quote.id)


@router.post("/{quote_id}/duplicate", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
async def duplicate_quote(
    quote_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> QuoteRead:
    import datetime as dt_mod
    source = await _load_quote(db, quote_id, tenant_id)
    new_no = await number_sequence.next_number(db, tenant_id, "quote")
    copy = Quote(
        tenant_id=tenant_id, customer_id=source.customer_id, quote_no=new_no,
        date=dt_mod.date.today(), subtotal=source.subtotal,
        vat_total=source.vat_total, total=source.total,
        notes=source.notes, internal_notes=source.internal_notes,
    )
    db.add(copy)
    await db.flush()
    groups_in = [
        QuoteGroupIn(title=g.title, position=g.position, items=[
            QuoteItemIn(description=i.description, qty=i.qty, unit=i.unit,
                        unit_price=i.unit_price, discount_pct=i.discount_pct,
                        vat_rate=i.vat_rate, material_id=i.material_id, position=i.position)
            for i in g.items
        ]) for g in source.groups
    ]
    items_in = [
        QuoteItemIn(description=i.description, qty=i.qty, unit=i.unit,
                    unit_price=i.unit_price, discount_pct=i.discount_pct,
                    vat_rate=i.vat_rate, material_id=i.material_id, position=i.position)
        for i in source.items
    ]
    await _create_items(db, copy.id, groups_in, items_in)
    await db.commit()
    return await _load_quote(db, copy.id)


@router.post("/{quote_id}/to-order", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def convert_to_order(
    quote_id: int,
    body: ConvertToOrderBody,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> OrderRead:
    quote = await _get_raw_or_404(db, quote_id, tenant_id)
    if quote.status != "accepted":
        raise HTTPException(400, "Nur angenommene Angebote können in Aufträge gewandelt werden.")
    loaded = await _load_quote(db, quote_id)
    if body.title:
        title = body.title
    elif loaded.groups:
        title = " · ".join(g.title for g in loaded.groups[:3])
    else:
        title = f"Aus Angebot {quote.quote_no}"
    order_no = await number_sequence.next_number(db, tenant_id, "order")
    order = Order(
        tenant_id=tenant_id, customer_id=quote.customer_id, quote_id=quote.id,
        order_no=order_no, title=title, status="open",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order, ["time_entries"])
    return OrderRead.model_validate(order)


@router.post("/{quote_id}/pdf")
async def generate_pdf(
    quote_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Response:
    quote = await _get_raw_or_404(db, quote_id, tenant_id)
    loaded = await _load_quote(db, quote_id)
    customer = await db.get(Customer, quote.customer_id)
    tenant = await db.get(Tenant, tenant_id)
    try:
        pdf_bytes = await pdf_service.render_quote_pdf(loaded, customer, tenant)
    except Exception as e:
        raise HTTPException(503, f"PDF nicht verfügbar: {e}")
    path = pdf_service.pdf_path(quote.quote_no)
    path.write_bytes(pdf_bytes)
    quote.pdf_path = str(path)
    await db.commit()
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{quote.quote_no}.pdf"'},
    )


async def _create_items(
    db: AsyncSession, quote_id: int, groups_in: list, items_in: list
) -> list[QuoteItem]:
    all_items: list[QuoteItem] = []
    global_pos = 1
    for g_idx, group_in in enumerate(groups_in):
        grp = QuoteGroup(
            quote_id=quote_id, title=group_in.title,
            position=getattr(group_in, "position", None) or (g_idx + 1),
        )
        db.add(grp)
        await db.flush()
        group_items: list[QuoteItem] = []
        for item_in in group_in.items:
            d = calculation.build_item(item_in, global_pos)
            qi = QuoteItem(quote_id=quote_id, group_id=grp.id, **d)
            db.add(qi)
            group_items.append(qi)
            all_items.append(qi)
            global_pos += 1
        await db.flush()
        grp.subtotal, grp.vat_total, grp.group_total = calculation.calc_totals(group_items)
    for item_in in items_in:
        d = calculation.build_item(item_in, global_pos)
        qi = QuoteItem(quote_id=quote_id, group_id=None, **d)
        db.add(qi)
        all_items.append(qi)
        global_pos += 1
    await db.flush()
    return all_items


async def _get_raw_or_404(db: AsyncSession, quote_id: int, tenant_id: int | None = None) -> Quote:
    q = select(Quote).where(Quote.id == quote_id)
    if tenant_id:
        q = q.where(Quote.tenant_id == tenant_id)
    qt = (await db.execute(q)).scalars().first()
    if not qt:
        raise HTTPException(404, "Angebot nicht gefunden")
    return qt


async def _load_quote(db: AsyncSession, quote_id: int, tenant_id: int | None = None) -> QuoteRead:
    q = (
        select(Quote)
        .options(selectinload(Quote.all_items), selectinload(Quote.groups).selectinload(QuoteGroup.items))
        .where(Quote.id == quote_id)
    )
    if tenant_id:
        q = q.where(Quote.tenant_id == tenant_id)
    qt = (await db.execute(q)).scalars().first()
    if not qt:
        raise HTTPException(404, "Angebot nicht gefunden")
    return _to_read(qt)


def _to_read(quote: Quote) -> QuoteRead:
    ungrouped = [i for i in quote.all_items if i.group_id is None]
    return QuoteRead(
        id=quote.id, tenant_id=quote.tenant_id, customer_id=quote.customer_id,
        quote_no=quote.quote_no, date=quote.date, valid_until=quote.valid_until,
        status=quote.status, subtotal=quote.subtotal, vat_total=quote.vat_total,
        total=quote.total, notes=quote.notes, internal_notes=quote.internal_notes,
        pdf_path=quote.pdf_path, version=quote.version,
        created_at=quote.created_at, updated_at=quote.updated_at,
        groups=[
            QuoteGroupRead(
                id=g.id, quote_id=g.quote_id, title=g.title, position=g.position,
                subtotal=g.subtotal, vat_total=g.vat_total, group_total=g.group_total,
                items=[QuoteItemRead.model_validate(i) for i in sorted(g.items, key=lambda x: x.position)],
            )
            for g in sorted(quote.groups, key=lambda x: x.position)
        ],
        items=[QuoteItemRead.model_validate(i) for i in sorted(ungrouped, key=lambda x: x.position)],
    )


async def _assert_customer(db: AsyncSession, customer_id: int, tenant_id: int) -> None:
    if not (await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    )).scalars().first():
        raise HTTPException(404, "Kunde nicht gefunden")


async def _update_position_history(
    db: AsyncSession, tenant_id: int, items: list[QuoteItem]
) -> None:
    now = datetime.now(timezone.utc)
    for item in items:
        existing = (await db.execute(
            select(PositionHistory).where(
                PositionHistory.tenant_id == tenant_id,
                PositionHistory.description == item.description,
                PositionHistory.unit == item.unit,
                PositionHistory.unit_price == item.unit_price,
            )
        )).scalars().first()
        if existing:
            existing.usage_count += 1
            existing.last_used_at = now
        else:
            db.add(PositionHistory(
                tenant_id=tenant_id, description=item.description,
                unit=item.unit, unit_price=item.unit_price,
                vat_rate=item.vat_rate, last_used_at=now,
            ))
    await db.flush()
