from decimal import Decimal

from pydantic import BaseModel


class MaterialBase(BaseModel):
    sku: str | None = None
    name: str
    description: str | None = None
    unit: str = "Stk"
    purchase_price: Decimal | None = None
    sale_price: Decimal | None = None
    vat_rate: Decimal = Decimal("19.00")
    category: str | None = None
    default_supplier_id: int | None = None
    active: bool = True


class MaterialCreate(MaterialBase):
    pass


class MaterialUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    description: str | None = None
    unit: str | None = None
    purchase_price: Decimal | None = None
    sale_price: Decimal | None = None
    vat_rate: Decimal | None = None
    category: str | None = None
    default_supplier_id: int | None = None
    active: bool | None = None


class MaterialRead(MaterialBase):
    id: int
    tenant_id: int
    usage_count: int

    model_config = {"from_attributes": True}


class MaterialListResponse(BaseModel):
    items: list[MaterialRead]
    total: int
