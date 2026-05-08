from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    iban: Mapped[str | None] = mapped_column(String(34), nullable=True)
    logo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invoice_number_prefix: Mapped[str | None] = mapped_column(String(10), nullable=True)
    quote_number_prefix: Mapped[str | None] = mapped_column(String(10), nullable=True)
    pdf_template: Mapped[str | None] = mapped_column(String(50), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="default_tenant")  # type: ignore[name-defined]
