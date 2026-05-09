import datetime as dt
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class SupplierInvoiceUpdate(BaseModel):
    supplier_id: int | None = None
    order_id: int | None = None
    external_no: str | None = None
    invoice_date: dt.date | None = None
    due_date: dt.date | None = None
    subtotal: Decimal | None = None
    vat_total: Decimal | None = None
    total: Decimal | None = None
    description: str | None = None
    status: str | None = None


class SupplierInvoiceRead(BaseModel):
    id: int
    tenant_id: int
    supplier_id: int | None
    order_id: int | None
    paperless_document_id: int | None
    original_filename: str | None
    external_no: str | None
    invoice_date: dt.date | None
    due_date: dt.date | None
    subtotal: Decimal | None
    vat_total: Decimal | None
    total: Decimal | None
    paid_at: datetime | None
    description: str | None
    status: str
    ocr_payload: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierInvoiceListResponse(BaseModel):
    items: list[SupplierInvoiceRead]
    total: int


class OcrSuggestion(BaseModel):
    supplier_name: str | None = None
    invoice_number: str | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    subtotal: str | None = None
    vat_total: str | None = None
    total: str | None = None
    description: str | None = None
