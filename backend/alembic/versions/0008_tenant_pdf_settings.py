"""tenant pdf settings: pdf_color, pdf_footer_text, pdf_show_bank_details, pdf_accent_secondary

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("pdf_color", sa.String(10), nullable=False, server_default="#1976D2"),
    )
    op.add_column(
        "tenants",
        sa.Column("pdf_footer_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("pdf_show_bank_details", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "tenants",
        sa.Column("pdf_accent_secondary", sa.String(10), nullable=False, server_default="#E3F2FD"),
    )


def downgrade() -> None:
    op.drop_column("tenants", "pdf_accent_secondary")
    op.drop_column("tenants", "pdf_show_bank_details")
    op.drop_column("tenants", "pdf_footer_text")
    op.drop_column("tenants", "pdf_color")
