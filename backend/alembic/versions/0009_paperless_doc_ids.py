"""paperless_doc_id auf quotes und invoices

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quotes", sa.Column("paperless_doc_id", sa.Integer(), nullable=True))
    op.add_column("invoices", sa.Column("paperless_doc_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "paperless_doc_id")
    op.drop_column("quotes", "paperless_doc_id")
