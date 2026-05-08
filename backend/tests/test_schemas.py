from decimal import Decimal

from app.schemas.customer import CustomerCreate, CustomerRead
from app.schemas.material import MaterialCreate
from app.schemas.supplier import SupplierCreate


def test_customer_create_defaults() -> None:
    c = CustomerCreate(name="Mustermann GmbH")
    assert c.kind == "privat"
    assert c.is_business is False
    assert c.e_invoice_format == "none"
    assert c.active is True


def test_customer_read_from_orm() -> None:
    from datetime import datetime, timezone

    data = {
        "id": 1,
        "tenant_id": 1,
        "customer_no": "K0001",
        "kind": "geschaeft",
        "name": "Test AG",
        "contact": None,
        "address": None,
        "email": "test@example.com",
        "phone": None,
        "tax_id": None,
        "notes": None,
        "is_business": True,
        "e_invoice_format": "xrechnung",
        "leitweg_id": None,
        "active": True,
        "created_at": datetime.now(timezone.utc),
    }
    read = CustomerRead.model_validate(data)
    assert read.customer_no == "K0001"
    assert read.is_business is True


def test_supplier_create() -> None:
    s = SupplierCreate(name="Baustoffhandel GmbH", iban="DE44500105175407324931")
    assert s.iban == "DE44500105175407324931"
    assert s.email is None


def test_material_create_defaults() -> None:
    m = MaterialCreate(name="Anfahrtspauschale")
    assert m.unit == "Stk"
    assert m.vat_rate == Decimal("19.00")
    assert m.active is True
