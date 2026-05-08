from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    sku: Mapped[str | None] = mapped_column(String(50), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="Stk")
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("19.00"))
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    tenant: Mapped["Tenant"] = relationship("Tenant")  # type: ignore[name-defined]
    default_supplier: Mapped["Supplier | None"] = relationship("Supplier")  # type: ignore[name-defined]
