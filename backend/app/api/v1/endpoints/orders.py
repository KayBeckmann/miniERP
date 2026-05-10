from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.invoice import Invoice, InvoiceItem
from app.models.order import Order, TimeEntry
from app.models.quote import Quote, QuoteGroup, QuoteItem
from app.schemas.invoice import InvoiceRead
from app.schemas.order import (
    OrderCreate, OrderListResponse, OrderRead, OrderUpdate,
    QuoteGroupSummary, TimeEntryCreate, TimeEntryRead, TimeEntryUpdate,
)
from app.schemas.quote import BillableItemRead, CreateInvoiceFromOrderBody
from app.services import calculation
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


# ── Global Time Entries ─────────────────────────────────────────────────────
# IMPORTANT: this route must be registered BEFORE /{order_id} to prevent
# FastAPI from matching "time-entries" as an integer path parameter.

@router.get("/time-entries", response_model=list[TimeEntryRead])
async def list_all_time_entries(
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[TimeEntry]:
    q = select(TimeEntry).join(Order).where(Order.tenant_id == tenant_id)
    if from_date:
        q = q.where(TimeEntry.entry_date >= from_date)
    if to_date:
        q = q.where(TimeEntry.entry_date <= to_date)
    result = await db.execute(
        q.options(selectinload(TimeEntry.quote_group)).order_by(TimeEntry.entry_date.desc())
    )
    return result.scalars().all()


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


# ── Time Entries (per order) ─────────────────────────────────────────────────

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


@router.get("/{order_id}/groups", response_model=list[QuoteGroupSummary])
async def get_order_groups(
    order_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[QuoteGroup]:
    order = await _get_or_404(db, order_id, tenant_id)
    if not order.quote_id:
        return []
    result = await db.execute(
        select(QuoteGroup).where(QuoteGroup.quote_id == order.quote_id).order_by(QuoteGroup.position)
    )
    return result.scalars().all()


@router.get("/{order_id}/billable-items", response_model=list[BillableItemRead])
async def get_billable_items(
    order_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[BillableItemRead]:
    """Gibt alle Angebots-Positionen des Auftrags zurück, mit Hinweis ob bereits abgerechnet."""
    order = await _get_or_404(db, order_id, tenant_id)
    if not order.quote_id:
        return []
    quote_items = (await db.execute(
        select(QuoteItem).where(QuoteItem.quote_id == order.quote_id).order_by(QuoteItem.position)
    )).scalars().all()

    result = []
    for qi in quote_items:
        # Prüfen ob diese QuoteItem-ID bereits in einer aktiven Rechnung steckt
        row = (await db.execute(
            select(Invoice.invoice_no)
            .join(InvoiceItem, InvoiceItem.invoice_id == Invoice.id)
            .where(
                InvoiceItem.quote_item_id == qi.id,
                Invoice.status != "cancelled",
            )
            .limit(1)
        )).first()
        result.append(BillableItemRead(
            id=qi.id,
            description=qi.description,
            qty=qi.qty,
            unit=qi.unit,
            unit_price=qi.unit_price,
            line_total=qi.line_total,
            already_invoiced=row is not None,
            invoice_no=row[0] if row else None,
        ))
    return result


@router.post("/{order_id}/to-invoice", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_invoice_from_order(
    order_id: int,
    body: CreateInvoiceFromOrderBody,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> InvoiceRead:
    from decimal import Decimal as D
    from sqlalchemy.orm import selectinload as sl

    order = await _get_or_404(db, order_id, tenant_id)
    inv_no = await next_number(db, tenant_id, "invoice")

    # Bereits abgerechnete Beträge aus früheren Teil-/Abschlagsrechnungen
    prior_invoiced_total = D("0.00")
    if body.kind == "final" and order.id:
        prior_rows = (await db.execute(
            select(Invoice.total)
            .where(
                Invoice.order_id == order.id,
                Invoice.kind.in_(["partial", "advance"]),
                Invoice.status != "cancelled",
            )
        )).all()
        prior_invoiced_total = sum((r[0] for r in prior_rows), D("0.00"))

    invoice = Invoice(
        tenant_id=tenant_id,
        customer_id=order.customer_id,
        order_id=order.id,
        quote_id=order.quote_id,
        invoice_no=inv_no,
        invoice_date=body.invoice_date,
        due_date=body.due_date,
        kind=body.kind,
        prior_invoiced_total=prior_invoiced_total,
    )
    db.add(invoice)
    await db.flush()

    inv_items: list[InvoiceItem] = []
    next_pos = 1

    if body.copy_items and order.quote_id:
        groups_result = await db.execute(
            select(QuoteGroup).where(QuoteGroup.quote_id == order.quote_id)
        )
        group_map: dict[int, str] = {g.id: g.title for g in groups_result.scalars().all()}

        all_items_result = await db.execute(
            select(QuoteItem).where(QuoteItem.quote_id == order.quote_id).order_by(QuoteItem.position)
        )
        quote_items = all_items_result.scalars().all()
        for qi in quote_items:
            # Bei Teilrechnungen: nur ausgewählte IDs, bei Schlussrechnungen: noch nicht abgerechnete
            if body.item_ids is not None:
                if qi.id not in body.item_ids:
                    continue
            elif body.kind in ("partial", "advance"):
                # Ohne explizite Auswahl: bereits abgerechnete überspringen
                already = (await db.execute(
                    select(InvoiceItem.id)
                    .join(Invoice, InvoiceItem.invoice_id == Invoice.id)
                    .where(InvoiceItem.quote_item_id == qi.id, Invoice.status != "cancelled")
                    .limit(1)
                )).first()
                if already:
                    continue
            ii = InvoiceItem(
                invoice_id=invoice.id,
                position=next_pos,
                description=qi.description,
                qty=qi.qty,
                unit=qi.unit,
                unit_price=qi.unit_price,
                discount_pct=qi.discount_pct,
                vat_rate=qi.vat_rate,
                line_total=qi.line_total,
                material_id=qi.material_id,
                quote_item_id=qi.id,
                group_label=group_map.get(qi.group_id) if qi.group_id else None,
            )
            db.add(ii)
            inv_items.append(ii)
            next_pos += 1

    if body.include_time_entries and order.time_entries:
        billable_entries = [e for e in order.time_entries if e.billable and not e.invoiced]
        if billable_entries:
            fallback = body.hourly_rate_default or D("0.00")
            total_hours = sum(e.hours for e in billable_entries)
            weighted_rates = [(e.hours, e.hourly_rate or fallback) for e in billable_entries]
            if any(r > 0 for _, r in weighted_rates):
                avg_rate = sum(h * r for h, r in weighted_rates) / sum(h for h, _ in weighted_rates)
            else:
                avg_rate = fallback
            line_total = (total_hours * avg_rate).quantize(D("0.01"))
            time_item = InvoiceItem(
                invoice_id=invoice.id,
                position=next_pos,
                description=f"Arbeitszeit — {order.title} ({len(billable_entries)} Buchungen)",
                qty=total_hours,
                unit="h",
                unit_price=avg_rate,
                discount_pct=D("0.00"),
                vat_rate=D("19.00"),
                line_total=line_total,
            )
            db.add(time_item)
            inv_items.append(time_item)
            for e in billable_entries:
                e.invoiced = True

    if inv_items:
        await db.flush()
        invoice.subtotal, invoice.vat_total, invoice.total = calculation.calc_totals(inv_items)

    await db.commit()
    result = await db.execute(
        select(Invoice)
        .options(sl(Invoice.items), sl(Invoice.payments))
        .where(Invoice.id == invoice.id)
    )
    inv = result.scalars().first()
    return InvoiceRead.model_validate(inv)


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
