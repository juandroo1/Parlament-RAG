"""api usage per day for the demo cost cap

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-17 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_usage",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("requests", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("cost_usd", sa.Double(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("day", name=op.f("pk_api_usage")),
    )


def downgrade() -> None:
    op.drop_table("api_usage")
