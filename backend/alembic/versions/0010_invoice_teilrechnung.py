"""invoice_item quote_item_id + invoice prior_invoiced_total"""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoice_items",
        sa.Column("quote_item_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_invoice_items_quote_item_id",
        "invoice_items", "quote_items",
        ["quote_item_id"], ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "invoices",
        sa.Column(
            "prior_invoiced_total",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="0.00",
        ),
    )


def downgrade() -> None:
    op.drop_column("invoices", "prior_invoiced_total")
    op.drop_constraint("fk_invoice_items_quote_item_id", "invoice_items", type_="foreignkey")
    op.drop_column("invoice_items", "quote_item_id")
