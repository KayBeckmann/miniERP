import datetime as dt
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, model_validator


class QuoteItemIn(BaseModel):
    description: str
    qty: Decimal
    unit: str
    unit_price: Decimal
    discount_pct: Decimal = Decimal("0.00")
    vat_rate: Decimal
    material_id: int | None = None
    position: int | None = None


class QuoteCreate(BaseModel):
    customer_id: int
    quote_date: dt.date
    valid_until: dt.date | None = None
    notes: str | None = None
    internal_notes: str | None = None
    items: list[QuoteItemIn] = []


class QuoteUpdate(BaseModel):
    customer_id: int | None = None
    quote_date: dt.date | None = None
    valid_until: dt.date | None = None
    notes: str | None = None
    internal_notes: str | None = None
    items: list[QuoteItemIn] | None = None


class QuoteStatusUpdate(BaseModel):
    status: Literal["draft", "sent", "accepted", "declined", "expired"]

    @model_validator(mode="after")
    def check_valid_status(self) -> "QuoteStatusUpdate":
        return self


class QuoteItemRead(BaseModel):
    id: int
    quote_id: int
    position: int
    description: str
    qty: Decimal
    unit: str
    unit_price: Decimal
    discount_pct: Decimal
    vat_rate: Decimal
    line_total: Decimal
    material_id: int | None

    model_config = {"from_attributes": True}


class QuoteRead(BaseModel):
    id: int
    tenant_id: int
    customer_id: int
    quote_no: str
    date: dt.date
    valid_until: dt.date | None
    status: str
    subtotal: Decimal
    vat_total: Decimal
    total: Decimal
    notes: str | None
    internal_notes: str | None
    pdf_path: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    items: list[QuoteItemRead] = []

    model_config = {"from_attributes": True}


class QuoteListResponse(BaseModel):
    items: list[QuoteRead]
    total: int


class PositionHistoryRead(BaseModel):
    id: int
    description: str
    unit: str
    unit_price: Decimal
    vat_rate: Decimal
    usage_count: int

    model_config = {"from_attributes": True}
