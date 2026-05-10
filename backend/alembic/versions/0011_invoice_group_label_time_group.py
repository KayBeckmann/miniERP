"""invoice_items group_label + time_entries quote_group_id"""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "invoice_items",
        sa.Column("group_label", sa.String(200), nullable=True),
    )
    op.add_column(
        "time_entries",
        sa.Column("quote_group_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_time_entries_quote_group_id",
        "time_entries", "quote_groups",
        ["quote_group_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_time_entries_quote_group_id", "time_entries", type_="foreignkey")
    op.drop_column("time_entries", "quote_group_id")
    op.drop_column("invoice_items", "group_label")
