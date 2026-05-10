import datetime as dt
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.schemas.quote import QuoteItemIn


class InvoiceCreate(BaseModel):
    customer_id: int
    order_id: int | None = None
    quote_id: int | None = None
    invoice_date: dt.date
    due_date: dt.date | None = None
    kind: Literal["final", "partial", "advance"] = "final"
    notes: str | None = None
    internal_notes: str | None = None
    items: list[QuoteItemIn] = []


class InvoiceUpdate(BaseModel):
    invoice_date: dt.date | None = None
    due_date: dt.date | None = None
    notes: str | None = None
    internal_notes: str | None = None
    items: list[QuoteItemIn] | None = None


class InvoiceStatusUpdate(BaseModel):
    status: Literal["draft", "sent", "paid", "overdue", "cancelled"]


class InvoiceItemRead(BaseModel):
    id: int
    position: int
    description: str
    qty: Decimal
    unit: str
    unit_price: Decimal
    discount_pct: Decimal
    vat_rate: Decimal
    line_total: Decimal
    material_id: int | None
    quote_item_id: int | None = None

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    payment_date: dt.date
    amount: Decimal
    method: Literal["transfer", "cash", "card"] = "transfer"
    bank_ref: str | None = None
    note: str | None = None


class PaymentRead(BaseModel):
    id: int
    invoice_id: int
    payment_date: dt.date
    amount: Decimal
    method: str
    bank_ref: str | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InvoiceRead(BaseModel):
    id: int
    tenant_id: int
    customer_id: int
    order_id: int | None
    quote_id: int | None
    invoice_no: str
    invoice_date: dt.date
    due_date: dt.date | None
    kind: str
    status: str
    subtotal: Decimal
    vat_total: Decimal
    total: Decimal
    paid_amount: Decimal
    prior_invoiced_total: Decimal = Decimal("0.00")
    paid_at: datetime | None
    notes: str | None
    internal_notes: str | None
    pdf_path: str | None
    pdf_sha256: str | None
    paperless_doc_id: int | None = None
    created_at: datetime
    updated_at: datetime
    items: list[InvoiceItemRead] = []
    payments: list[PaymentRead] = []

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    items: list[InvoiceRead]
    total: int
