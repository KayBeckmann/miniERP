"""Lieferantenrechnungen — Upload zu Paperless-ngx, OCR-Strukturierung via Ollama."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, get_tenant_id
from app.models.supplier_invoice import SupplierInvoice
from app.schemas.supplier_invoice import (
    OcrSuggestion,
    SupplierInvoiceListResponse,
    SupplierInvoiceRead,
    SupplierInvoiceUpdate,
)
from app.services import ollama as ollama_svc
from app.services import paperless as paperless_svc

router = APIRouter()


# ── Liste ───────────────────────────────────────────────────────────────────

@router.get("", response_model=SupplierInvoiceListResponse)
async def list_supplier_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    status_filter: str | None = Query(None, alias="status"),
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> SupplierInvoiceListResponse:
    q = select(SupplierInvoice).where(SupplierInvoice.tenant_id == tenant_id)
    if status_filter:
        q = q.where(SupplierInvoice.status == status_filter)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    items = (
        await db.execute(q.order_by(SupplierInvoice.created_at.desc()).offset(skip).limit(limit))
    ).scalars().all()
    return SupplierInvoiceListResponse(
        items=[SupplierInvoiceRead.model_validate(i) for i in items], total=total
    )


# ── Upload → Paperless ──────────────────────────────────────────────────────

@router.post("", response_model=SupplierInvoiceRead, status_code=status.HTTP_201_CREATED)
async def upload_supplier_invoice(
    file: UploadFile = File(...),
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> SupplierInvoice:
    content = await file.read()
    if not content:
        raise HTTPException(400, "Leere Datei")

    mime = file.content_type or "application/octet-stream"
    filename = file.filename or "upload"

    # 1. Zu Paperless hochladen
    try:
        result = await paperless_svc.upload_document(filename, content, mime)
    except Exception as e:
        raise HTTPException(502, f"Paperless-Upload fehlgeschlagen: {e}")

    # Paperless gibt Task-UUID oder document_id zurück
    paperless_doc_id: int | None = None
    task_id: str | None = None
    if isinstance(result, int):
        paperless_doc_id = result
    else:
        task_id = str(result)

    # 2. SupplierInvoice anlegen
    si = SupplierInvoice(
        tenant_id=tenant_id,
        paperless_document_id=paperless_doc_id,
        original_filename=filename,
        status="draft",
    )
    db.add(si)
    await db.commit()
    await db.refresh(si)

    # 3. OCR asynchron holen (wenn document_id bekannt)
    if paperless_doc_id:
        await _fetch_and_structure(db, si, paperless_doc_id, tenant_id)

    return si


# ── Webhook von n8n (Paperless → miniERP) ──────────────────────────────────

@router.post("/from-paperless/{document_id}", response_model=SupplierInvoiceRead, status_code=status.HTTP_201_CREATED)
async def from_paperless_webhook(
    document_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> SupplierInvoice:
    # Doppelverarbeitung verhindern
    existing = (
        await db.execute(
            select(SupplierInvoice).where(
                SupplierInvoice.paperless_document_id == document_id,
                SupplierInvoice.tenant_id == tenant_id,
            )
        )
    ).scalars().first()
    if existing:
        return existing

    si = SupplierInvoice(
        tenant_id=tenant_id,
        paperless_document_id=document_id,
        status="draft",
    )
    db.add(si)
    await db.commit()
    await db.refresh(si)
    await _fetch_and_structure(db, si, document_id, tenant_id)
    return si


# ── Detail + Update ─────────────────────────────────────────────────────────

@router.get("/{si_id}", response_model=SupplierInvoiceRead)
async def get_supplier_invoice(
    si_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> SupplierInvoice:
    return await _get_or_404(db, si_id, tenant_id)


@router.patch("/{si_id}", response_model=SupplierInvoiceRead)
async def update_supplier_invoice(
    si_id: int,
    body: SupplierInvoiceUpdate,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> SupplierInvoice:
    si = await _get_or_404(db, si_id, tenant_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(si, k, v)
    si.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(si)

    # Custom Fields in Paperless aktualisieren (best-effort)
    if si.paperless_document_id:
        fields: dict[str, str] = {}
        if si.external_no:
            fields["rechnung_no"] = si.external_no
        if si.order_id:
            fields["auftrag_no"] = str(si.order_id)
        if fields:
            await paperless_svc.set_custom_fields(si.paperless_document_id, fields)

    return si


@router.delete("/{si_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier_invoice(
    si_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> None:
    si = await _get_or_404(db, si_id, tenant_id)
    await db.delete(si)
    await db.commit()


# ── OCR-Strukturierung neu triggern ────────────────────────────────────────

@router.post("/{si_id}/structure", response_model=OcrSuggestion)
async def structure_invoice(
    si_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> OcrSuggestion:
    si = await _get_or_404(db, si_id, tenant_id)
    if not si.paperless_document_id:
        raise HTTPException(400, "Kein Paperless-Dokument verknüpft")
    await _fetch_and_structure(db, si, si.paperless_document_id, tenant_id)
    return OcrSuggestion(**(si.ocr_payload or {}))


# ── Paperless-Dokument anzeigen ─────────────────────────────────────────────

@router.get("/{si_id}/paperless")
async def paperless_detail(
    si_id: int,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
) -> dict:
    si = await _get_or_404(db, si_id, tenant_id)
    if not si.paperless_document_id:
        raise HTTPException(404, "Kein Paperless-Dokument verknüpft")
    try:
        doc = await paperless_svc.get_document(si.paperless_document_id)
        return {
            "id": doc.get("id"),
            "title": doc.get("title"),
            "created": doc.get("created"),
            "content_preview": (doc.get("content") or "")[:500],
            "paperless_url": f"{__import__('app.core.config', fromlist=['settings']).settings.PAPERLESS_URL}/documents/{si.paperless_document_id}/details",
        }
    except Exception as e:
        raise HTTPException(502, f"Paperless nicht erreichbar: {e}")


# ── Helpers ─────────────────────────────────────────────────────────────────

async def _get_or_404(db: AsyncSession, si_id: int, tenant_id: int) -> SupplierInvoice:
    result = await db.execute(
        select(SupplierInvoice).where(
            SupplierInvoice.id == si_id, SupplierInvoice.tenant_id == tenant_id
        )
    )
    si = result.scalars().first()
    if not si:
        raise HTTPException(404, "Eingangsrechnung nicht gefunden")
    return si


async def _fetch_and_structure(
    db: AsyncSession, si: SupplierInvoice, doc_id: int, tenant_id: int
) -> None:
    try:
        ocr_text = await paperless_svc.get_document_content(doc_id)
        si.ocr_text = ocr_text[:10000]  # Limit

        if ocr_text.strip():
            structured = await ollama_svc.structure_invoice(ocr_text)
            si.ocr_payload = structured

            # Felder automatisch vorbelegen (User bestätigt später)
            if not si.external_no and structured.get("invoice_number"):
                si.external_no = str(structured["invoice_number"])
            if not si.invoice_date and structured.get("invoice_date"):
                try:
                    import datetime as dt
                    si.invoice_date = dt.date.fromisoformat(structured["invoice_date"])
                except (ValueError, TypeError):
                    pass
            if not si.due_date and structured.get("due_date"):
                try:
                    import datetime as dt
                    si.due_date = dt.date.fromisoformat(structured["due_date"])
                except (ValueError, TypeError):
                    pass
            from decimal import Decimal, InvalidOperation
            for field, attr in [("subtotal", "subtotal"), ("vat_total", "vat_total"), ("total", "total")]:
                if not getattr(si, attr) and structured.get(field):
                    try:
                        setattr(si, attr, Decimal(str(structured[field]).replace(",", ".")))
                    except InvalidOperation:
                        pass
            if not si.description and structured.get("description"):
                si.description = str(structured["description"])

        si.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(si)
    except Exception:
        pass  # OCR-Fehler sollen den Upload nicht blockieren
