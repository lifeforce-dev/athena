"""Add per-user risk thresholds (critical, tight) to users.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-04-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "risk_critical_threshold",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="500.00",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "risk_tight_threshold",
            sa.Numeric(12, 2),
            nullable=False,
            server_default="1000.00",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "risk_tight_threshold")
    op.drop_column("users", "risk_critical_threshold")
