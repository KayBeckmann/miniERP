"""angebotsgruppen: quote_groups + group_id in quote_items

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quote_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quote_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("vat_total", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("group_total", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quote_groups_quote_id", "quote_groups", ["quote_id"])

    # group_id spalte zu quote_items hinzufügen (nullable — bestehende Items bleiben ungrouped)
    op.add_column(
        "quote_items",
        sa.Column("group_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_quote_items_group_id",
        "quote_items", "quote_groups",
        ["group_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_quote_items_group_id", "quote_items", type_="foreignkey")
    op.drop_column("quote_items", "group_id")
    op.drop_index("ix_quote_groups_quote_id", "quote_groups")
    op.drop_table("quote_groups")
