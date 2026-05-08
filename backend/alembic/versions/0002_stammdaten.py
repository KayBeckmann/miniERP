"""stammdaten: customers, suppliers, materials

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-08
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("customer_no", sa.String(20), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="privat"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("contact", sa.String(200), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("tax_id", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_business", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("e_invoice_format", sa.String(20), nullable=False, server_default="none"),
        sa.Column("leitweg_id", sa.String(50), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_tenant_id", "customers", ["tenant_id"])

    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("iban", sa.String(34), nullable=True),
        sa.Column("default_payment_terms", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_suppliers_tenant_id", "suppliers", ["tenant_id"])

    op.create_table(
        "materials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("sku", sa.String(50), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(20), nullable=False, server_default="Stk"),
        sa.Column("purchase_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("sale_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False, server_default="19.00"),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("default_supplier_id", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["default_supplier_id"], ["suppliers.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_materials_tenant_id", "materials", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_materials_tenant_id", "materials")
    op.drop_table("materials")
    op.drop_index("ix_suppliers_tenant_id", "suppliers")
    op.drop_table("suppliers")
    op.drop_index("ix_customers_tenant_id", "customers")
    op.drop_table("customers")
