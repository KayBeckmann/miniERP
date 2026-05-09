from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SupplierInvoice(Base):
    __tablename__ = "supplier_invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), nullable=True)

    # Paperless-Referenz
    paperless_document_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Lieferanten-Rechnungsdaten (aus OCR + User-Bestätigung)
    external_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    vat_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status: draft (unbestätigt), confirmed, paid
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")

    # OCR + KI-Vorschlag
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    supplier: Mapped["Supplier | None"] = relationship("Supplier")  # type: ignore[name-defined]
    order: Mapped["Order | None"] = relationship("Order")  # type: ignore[name-defined]
