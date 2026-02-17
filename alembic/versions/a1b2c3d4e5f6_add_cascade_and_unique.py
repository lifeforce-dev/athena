"""Add ON DELETE CASCADE to all FKs and UNIQUE on gmail_subscriptions.user_id.

Revision ID: a1b2c3d4e5f6
Revises: 6c52f14865f5
Create Date: 2026-02-16 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "6c52f14865f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, constraint_name, column, referred_table, referred_column)
_FK_SPECS = [
    ("commitments", "fk_commitments_user_id", "user_id", "users", "id"),
    ("balance_snapshots", "fk_balance_snapshots_user_id", "user_id", "users", "id"),
    ("transactions", "fk_transactions_user_id", "user_id", "users", "id"),
    ("gmail_subscriptions", "fk_gmail_subscriptions_user_id", "user_id", "users", "id"),
]


def upgrade() -> None:
    # Recreate all FKs with ON DELETE CASCADE.
    for table, name, col, ref_table, ref_col in _FK_SPECS:
        op.drop_constraint(f"{table}_{col}_fkey", table, type_="foreignkey")
        op.create_foreign_key(name, table, ref_table, [col], [ref_col], ondelete="CASCADE")

    # One Gmail subscription per user.
    op.create_unique_constraint("uq_gmail_subscriptions_user_id", "gmail_subscriptions", ["user_id"])


def downgrade() -> None:
    op.drop_constraint("uq_gmail_subscriptions_user_id", "gmail_subscriptions", type_="unique")

    # Restore original FKs without CASCADE.
    for table, name, col, ref_table, ref_col in _FK_SPECS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(f"{table}_{col}_fkey", table, ref_table, [col], [ref_col])
