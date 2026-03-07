"""Drop all Gmail remnants.

Gmail integration has been fully replaced by Teller. Removes the
gmail_subscriptions table, gmail_message_id columns, their unique
constraints, and updates source defaults from 'gmail' to 'teller'.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-03-06 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: str | Sequence[str] | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("gmail_subscriptions")

    # Drop gmail unique constraints and columns from balance_snapshots.
    op.drop_constraint("uq_balance_user_gmail", "balance_snapshots", type_="unique")
    op.drop_column("balance_snapshots", "gmail_message_id")

    # Drop gmail unique constraints and columns from transactions.
    op.drop_constraint("uq_transaction_user_gmail", "transactions", type_="unique")
    op.drop_column("transactions", "gmail_message_id")

    # Update server_default on source columns from 'gmail' to 'teller'.
    op.alter_column(
        "transactions",
        "source",
        server_default="teller",
    )
    op.alter_column(
        "balance_snapshots",
        "source",
        server_default="teller",
    )


def downgrade() -> None:
    # Restore original server defaults.
    op.alter_column(
        "balance_snapshots",
        "source",
        server_default="gmail",
    )
    op.alter_column(
        "transactions",
        "source",
        server_default="gmail",
    )

    # Restore gmail_message_id columns and constraints.
    op.add_column("transactions", sa.Column("gmail_message_id", sa.String(64), nullable=True))
    op.create_unique_constraint(
        "uq_transaction_user_gmail", "transactions", ["user_id", "gmail_message_id"]
    )

    op.add_column("balance_snapshots", sa.Column("gmail_message_id", sa.String(64), nullable=True))
    op.create_unique_constraint(
        "uq_balance_user_gmail", "balance_snapshots", ["user_id", "gmail_message_id"]
    )

    op.create_table(
        "gmail_subscriptions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("gmail_address", sa.String(255), nullable=False),
        sa.Column("history_id", sa.String(64)),
        sa.Column("watch_expiry", sa.DateTime(timezone=True)),
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
