from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CustomerBase(BaseModel):
    kind: Literal["privat", "geschaeft"] = "privat"
    name: str
    contact: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    tax_id: str | None = None
    notes: str | None = None
    is_business: bool = False
    e_invoice_format: Literal["none", "xrechnung", "zugferd"] = "none"
    leitweg_id: str | None = None
    active: bool = True


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    kind: Literal["privat", "geschaeft"] | None = None
    name: str | None = None
    contact: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    tax_id: str | None = None
    notes: str | None = None
    is_business: bool | None = None
    e_invoice_format: Literal["none", "xrechnung", "zugferd"] | None = None
    leitweg_id: str | None = None
    active: bool | None = None


class CustomerRead(CustomerBase):
    id: int
    tenant_id: int
    customer_no: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    items: list[CustomerRead]
    total: int
