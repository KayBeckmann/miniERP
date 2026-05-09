"""ausgangsrechnungen + zahlungen

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("quote_id", sa.Integer(), nullable=True),
        sa.Column("invoice_no", sa.String(30), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("kind", sa.String(20), nullable=False, server_default="final"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("vat_total", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("paid_amount", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("pdf_path", sa.String(255), nullable=True),
        sa.Column("pdf_sha256", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoices_tenant_id", "invoices", ["tenant_id"])

    op.create_table(
        "invoice_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("qty", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_pct", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("method", sa.String(20), nullable=False, server_default="transfer"),
        sa.Column("bank_ref", sa.String(100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_payments_invoice_id", "payments")
    op.drop_table("payments")
    op.drop_index("ix_invoice_items_invoice_id", "invoice_items")
    op.drop_table("invoice_items")
    op.drop_index("ix_invoices_tenant_id", "invoices")
    op.drop_table("invoices")
