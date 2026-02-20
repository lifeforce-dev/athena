"""Replace tour_completed_at with completed_tours.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-20 06:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("completed_tours", sa.Text(), nullable=True))
    op.drop_column("users", "tour_completed_at")


def downgrade() -> None:
    op.add_column("users", sa.Column("tour_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.drop_column("users", "completed_tours")
