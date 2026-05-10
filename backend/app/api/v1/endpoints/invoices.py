import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceItem, Payment
from app.models.tenant import Tenant
from app.schemas.invoice import (
    InvoiceCreate, InvoiceListResponse, InvoiceRead,
    InvoiceStatusUpdate, InvoiceUpdate, PaymentCreate, PaymentRead,
)
from app.services import calculation, number_sequence, pdf as pdf_service
from app.services import paperless as paperless_service

router = APIRouter()

_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["sent"],
    "sent": ["paid", "overdue", "cancelled"],
    "paid": [],
    "overdue": ["paid", "cancelled"],
    "cancelled": [],
}


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> InvoiceListResponse:
    q = select(Invoice).options(
        selectinload(Invoice.items), selectinload(Invoice.payments)
    ).where(Invoice.tenant_id == tenant_id)
    if status_filter:
        q = q.where(Invoice.status == status_filter)
    if search:
        like = f"%{search}%"
        q = q.join(Customer, Invoice.customer_id == Customer.id).where(
            or_(Invoice.invoice_no.ilike(like), Customer.name.ilike(like))
        )
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    invoices = (
        await db.execute(q.order_by(Invoice.invoice_date.desc()).offset(skip).limit(limit))
    ).scalars().all()
    return InvoiceListResponse(
        items=[InvoiceRead.model_validate(i) for i in invoices], total=total
    )


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: InvoiceCreate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Invoice:
    inv_no = await number_sequence.next_number(db, tenant_id, "invoice")
    invoice = Invoice(
        tenant_id=tenant_id, customer_id=body.customer_id, order_id=body.order_id,
        quote_id=body.quote_id, invoice_no=inv_no, invoice_date=body.invoice_date,
        due_date=body.due_date, kind=body.kind, notes=body.notes, internal_notes=body.internal_notes,
    )
    db.add(invoice)
    await db.flush()
    built = calculation.build_items(body.items)
    for d in built:
        db.add(InvoiceItem(invoice_id=invoice.id, **d))
    await db.flush()
    await db.refresh(invoice, ["items"])
    invoice.subtotal, invoice.vat_total, invoice.total = calculation.calc_totals(invoice.items)
    await db.commit()
    await db.refresh(invoice, ["items", "payments"])
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(
    invoice_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Invoice:
    return await _get_or_404(db, invoice_id, tenant_id)


@router.patch("/{invoice_id}", response_model=InvoiceRead)
async def update_invoice(
    invoice_id: int,
    body: InvoiceUpdate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Invoice:
    invoice = await _get_or_404(db, invoice_id, tenant_id)
    if invoice.status != "draft":
        raise HTTPException(400, "Nur Entwürfe können bearbeitet werden.")
    for k, v in body.model_dump(exclude_unset=True, exclude={"items"}).items():
        setattr(invoice, k, v)
    if body.items is not None:
        for item in invoice.items:
            await db.delete(item)
        await db.flush()
        for d in calculation.build_items(body.items):
            db.add(InvoiceItem(invoice_id=invoice.id, **d))
        await db.flush()
        await db.refresh(invoice, ["items"])
        invoice.subtotal, invoice.vat_total, invoice.total = calculation.calc_totals(invoice.items)
    invoice.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(invoice, ["items", "payments"])
    return invoice


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> None:
    invoice = await _get_or_404(db, invoice_id, tenant_id)
    if invoice.status != "draft":
        raise HTTPException(400, "Nur Entwürfe können gelöscht werden.")
    await db.delete(invoice)
    await db.commit()


@router.patch("/{invoice_id}/status", response_model=InvoiceRead)
async def update_status(
    invoice_id: int,
    body: InvoiceStatusUpdate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Invoice:
    invoice = await _get_or_404(db, invoice_id, tenant_id)
    allowed = _TRANSITIONS.get(invoice.status, [])
    if body.status not in allowed:
        raise HTTPException(400, f"Übergang '{invoice.status}' → '{body.status}' nicht erlaubt.")
    invoice.status = body.status
    invoice.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(invoice, ["items", "payments"])
    return invoice


@router.post("/{invoice_id}/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def add_payment(
    invoice_id: int,
    body: PaymentCreate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Payment:
    invoice = await _get_or_404(db, invoice_id, tenant_id)
    payment = Payment(**body.model_dump(), invoice_id=invoice_id, tenant_id=tenant_id)
    db.add(payment)
    await db.flush()
    await db.refresh(invoice, ["payments"])
    invoice.paid_amount = sum(p.amount for p in invoice.payments)
    if invoice.paid_amount >= invoice.total:
        invoice.status = "paid"
        invoice.paid_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(payment)
    return payment


@router.get("/{invoice_id}/preview")
async def preview_invoice(
    invoice_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Response:
    """Gibt die Rechnung als HTML zurück (kein Gotenberg, sofortige Vorschau)."""
    invoice = await _get_or_404(db, invoice_id, tenant_id)
    customer = await db.get(Customer, invoice.customer_id)
    tenant = await db.get(Tenant, tenant_id)
    html = pdf_service.render_invoice_html(invoice, customer, tenant)
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/{invoice_id}/pdf")
async def generate_pdf(
    invoice_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> Response:
    invoice = await _get_or_404(db, invoice_id, tenant_id)
    customer = await db.get(Customer, invoice.customer_id)
    tenant = await db.get(Tenant, tenant_id)
    try:
        pdf_bytes = await pdf_service.render_invoice_pdf(invoice, customer, tenant)
    except Exception as e:
        raise HTTPException(503, f"PDF nicht verfügbar: {e}")
    sha = hashlib.sha256(pdf_bytes).hexdigest()
    path = pdf_service.invoice_pdf_path(invoice.invoice_no)
    path.write_bytes(pdf_bytes)
    invoice.pdf_path = str(path)
    invoice.pdf_sha256 = sha

    # Paperless-ngx: PDF automatisch hochladen (graceful wenn offline)
    if not invoice.paperless_doc_id:
        try:
            doc_id = await paperless_service.upload_document(
                filename=f"{invoice.invoice_no}.pdf",
                content=pdf_bytes,
            )
            if isinstance(doc_id, int) and doc_id > 0:
                invoice.paperless_doc_id = doc_id
                await paperless_service.set_custom_fields(doc_id, {
                    "rechnung_no": invoice.invoice_no,
                    "sparte": tenant.code if tenant else "",
                })
        except Exception:
            pass

    await db.commit()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice.invoice_no}.pdf"'},
    )


async def _get_or_404(db: AsyncSession, invoice_id: int, tenant_id: int) -> Invoice:
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.items), selectinload(Invoice.payments))
        .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
    )
    invoice = result.scalars().first()
    if not invoice:
        raise HTTPException(404, "Rechnung nicht gefunden")
    return invoice
