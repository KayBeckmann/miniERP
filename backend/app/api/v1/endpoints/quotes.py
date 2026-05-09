from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.customer import Customer
from app.models.quote import PositionHistory, Quote, QuoteItem
from app.models.tenant import Tenant
from app.schemas.quote import (
    PositionHistoryRead,
    QuoteCreate,
    QuoteListResponse,
    QuoteRead,
    QuoteStatusUpdate,
    QuoteUpdate,
)
from app.services import calculation, number_sequence, pdf

router = APIRouter()

# Valid status transitions
_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["sent", "expired"],
    "sent": ["accepted", "declined", "expired"],
    "accepted": ["draft"],
    "declined": [],
    "expired": [],
}


# ── Position History ────────────────────────────────────────────────────────

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


# ── Quote CRUD ──────────────────────────────────────────────────────────────

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
        .options(selectinload(Quote.items), selectinload(Quote.customer))
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
    quotes = (
        await db.execute(q.order_by(Quote.date.desc()).offset(skip).limit(limit))
    ).scalars().all()
    return QuoteListResponse(items=[QuoteRead.model_validate(q) for q in quotes], total=total)


@router.post("", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
async def create_quote(
    body: QuoteCreate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Quote:
    await _assert_customer(db, body.customer_id, tenant_id)
    quote_no = await number_sequence.next_number(db, tenant_id, "quote")

    quote = Quote(
        tenant_id=tenant_id,
        customer_id=body.customer_id,
        quote_no=quote_no,
        date=body.quote_date,
        valid_until=body.valid_until,
        notes=body.notes,
        internal_notes=body.internal_notes,
    )
    db.add(quote)
    await db.flush()

    built = calculation.build_items(body.items)
    for d in built:
        db.add(QuoteItem(quote_id=quote.id, **d))
    await db.flush()

    await db.refresh(quote, ["items"])
    quote.subtotal, quote.vat_total, quote.total = calculation.calc_totals(quote.items)
    await db.commit()
    await db.refresh(quote, ["items", "customer"])

    await _update_position_history(db, tenant_id, quote.items)
    return quote


@router.get("/{quote_id}", response_model=QuoteRead)
async def get_quote(
    quote_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Quote:
    return await _get_or_404(db, quote_id, tenant_id)


@router.patch("/{quote_id}", response_model=QuoteRead)
async def update_quote(
    quote_id: int,
    body: QuoteUpdate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Quote:
    quote = await _get_or_404(db, quote_id, tenant_id)
    if quote.status not in ("draft",):
        raise HTTPException(400, "Nur Entwürfe können bearbeitet werden.")

    for attr, field in [("customer_id", "customer_id"), ("date", "quote_date"),
                         ("valid_until", "valid_until"), ("notes", "notes"),
                         ("internal_notes", "internal_notes")]:
        value = getattr(body, field, None)
        if value is not None:
            setattr(quote, attr, value)

    if body.items is not None:
        for item in quote.items:
            await db.delete(item)
        await db.flush()
        built = calculation.build_items(body.items)
        for d in built:
            db.add(QuoteItem(quote_id=quote.id, **d))
        await db.flush()
        await db.refresh(quote, ["items"])
        quote.subtotal, quote.vat_total, quote.total = calculation.calc_totals(quote.items)
        await _update_position_history(db, tenant_id, quote.items)

    quote.updated_at = datetime.now(timezone.utc)
    quote.version += 1
    await db.commit()
    await db.refresh(quote, ["items", "customer"])
    return quote


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(
    quote_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> None:
    quote = await _get_or_404(db, quote_id, tenant_id)
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
) -> Quote:
    quote = await _get_or_404(db, quote_id, tenant_id)
    allowed = _TRANSITIONS.get(quote.status, [])
    if body.status not in allowed:
        raise HTTPException(
            400, f"Übergang von '{quote.status}' → '{body.status}' nicht erlaubt."
        )
    quote.status = body.status
    quote.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(quote, ["items", "customer"])
    return quote


@router.post("/{quote_id}/duplicate", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
async def duplicate_quote(
    quote_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Quote:
    source = await _get_or_404(db, quote_id, tenant_id)
    from datetime import date as date_cls

    new_no = await number_sequence.next_number(db, tenant_id, "quote")
    copy = Quote(
        tenant_id=tenant_id,
        customer_id=source.customer_id,
        quote_no=new_no,
        date=date_cls.today(),
        valid_until=None,
        notes=source.notes,
        internal_notes=source.internal_notes,
        subtotal=source.subtotal,
        vat_total=source.vat_total,
        total=source.total,
    )
    db.add(copy)
    await db.flush()
    for item in source.items:
        db.add(QuoteItem(
            quote_id=copy.id,
            position=item.position,
            description=item.description,
            qty=item.qty,
            unit=item.unit,
            unit_price=item.unit_price,
            discount_pct=item.discount_pct,
            vat_rate=item.vat_rate,
            line_total=item.line_total,
            material_id=item.material_id,
        ))
    await db.commit()
    await db.refresh(copy, ["items", "customer"])
    return copy


@router.post("/{quote_id}/pdf")
async def generate_pdf(
    quote_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Response:
    quote = await _get_or_404(db, quote_id, tenant_id)
    customer = await db.get(Customer, quote.customer_id)
    tenant = await db.get(Tenant, tenant_id)

    try:
        pdf_bytes = await pdf.render_quote_pdf(quote, customer, tenant)
    except Exception as e:
        raise HTTPException(503, f"PDF-Generierung nicht verfügbar: {e}")

    path = pdf.pdf_path(quote.quote_no)
    path.write_bytes(pdf_bytes)
    quote.pdf_path = str(path)
    await db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{quote.quote_no}.pdf"'},
    )


# ── Helpers ─────────────────────────────────────────────────────────────────

async def _get_or_404(db: AsyncSession, quote_id: int, tenant_id: int) -> Quote:
    result = await db.execute(
        select(Quote)
        .options(selectinload(Quote.items), selectinload(Quote.customer))
        .where(Quote.id == quote_id, Quote.tenant_id == tenant_id)
    )
    quote = result.scalars().first()
    if not quote:
        raise HTTPException(404, "Angebot nicht gefunden")
    return quote


async def _assert_customer(db: AsyncSession, customer_id: int, tenant_id: int) -> None:
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    )
    if not result.scalars().first():
        raise HTTPException(404, "Kunde nicht gefunden")


async def _update_position_history(
    db: AsyncSession, tenant_id: int, items: list[QuoteItem]
) -> None:
    now = datetime.now(timezone.utc)
    for item in items:
        existing = (
            await db.execute(
                select(PositionHistory).where(
                    PositionHistory.tenant_id == tenant_id,
                    PositionHistory.description == item.description,
                    PositionHistory.unit == item.unit,
                    PositionHistory.unit_price == item.unit_price,
                )
            )
        ).scalars().first()

        if existing:
            existing.usage_count += 1
            existing.last_used_at = now
        else:
            db.add(PositionHistory(
                tenant_id=tenant_id,
                description=item.description,
                unit=item.unit,
                unit_price=item.unit_price,
                vat_rate=item.vat_rate,
                last_used_at=now,
            ))
    await db.flush()
