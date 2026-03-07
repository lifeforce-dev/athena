"""Add Teller bank integration schema.

Creates the teller_enrollments table and adds source/teller columns
to the existing transactions table.

Revision ID: b1c2d3e4f5a6
Revises: b8c9d0e1f2a3
Create Date: 2026-03-04 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- New table: teller_enrollments --
    op.create_table(
        "teller_enrollments",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("enrollment_id", sa.String(128), unique=True, nullable=False),
        sa.Column("institution_name", sa.String(255), nullable=False),
        sa.Column("access_token_encrypted", sa.Text, nullable=False),
        sa.Column("account_id", sa.String(128), nullable=True),
        sa.Column("account_name", sa.String(255), nullable=True),
        sa.Column("account_currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("status", sa.String(32), nullable=False, server_default="awaiting_account"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("idx_teller_enrollment_user", "teller_enrollments", ["user_id"])

    # Partial unique index: only one active enrollment per user.
    op.execute(
        "CREATE UNIQUE INDEX uq_teller_user_active ON teller_enrollments (user_id) "
        "WHERE status IN ('awaiting_account', 'active', 'syncing')"
    )

    # -- Modify: transactions --
    op.add_column(
        "transactions",
        sa.Column("source", sa.String(32), nullable=False, server_default="gmail"),
    )
    op.add_column(
        "transactions",
        sa.Column("teller_transaction_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("category", sa.String(128), nullable=True),
    )
    op.create_unique_constraint(
        "uq_transaction_user_teller",
        "transactions",
        ["user_id", "teller_transaction_id"],
    )


def downgrade() -> None:
    # -- Undo: transactions --
    op.drop_constraint("uq_transaction_user_teller", "transactions", type_="unique")
    op.drop_column("transactions", "category")
    op.drop_column("transactions", "teller_transaction_id")
    op.drop_column("transactions", "source")

    # -- Undo: teller_enrollments --
    op.drop_index("uq_teller_user_active", table_name="teller_enrollments")
    op.drop_index("idx_teller_enrollment_user", table_name="teller_enrollments")
    op.drop_table("teller_enrollments")
