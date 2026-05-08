from pydantic import BaseModel


class SupplierBase(BaseModel):
    name: str
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    iban: str | None = None
    default_payment_terms: str | None = None
    notes: str | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    iban: str | None = None
    default_payment_terms: str | None = None
    notes: str | None = None


class SupplierRead(SupplierBase):
    id: int
    tenant_id: int

    model_config = {"from_attributes": True}


class SupplierListResponse(BaseModel):
    items: list[SupplierRead]
    total: int
