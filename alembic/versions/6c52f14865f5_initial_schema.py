"""initial schema

Revision ID: 6c52f14865f5
Revises: 
Create Date: 2026-02-16 15:54:35.116988

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c52f14865f5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- users --
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("discord_id", sa.String(32), unique=True, nullable=False),
        sa.Column("discord_username", sa.String(128), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_users_discord_id", "users", ["discord_id"])

    # -- commitments --
    op.create_table(
        "commitments",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("frequency", sa.String(32), nullable=False),
        sa.Column("day_of_month", sa.Integer, nullable=True),
        sa.Column("anchor_date", sa.Date, nullable=True),
        sa.Column("one_time_date", sa.Date, nullable=True),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("is_paycheck", sa.Boolean, default=False, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_commitments_user_id", "commitments", ["user_id"])
    op.create_index("idx_commitments_user_active", "commitments", ["user_id", "is_active"])

    # -- balance_snapshots --
    op.create_table(
        "balance_snapshots",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("account_label", sa.String(64), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(32), nullable=False, server_default="gmail"),
        sa.Column("gmail_message_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_balance_user_gmail", "balance_snapshots", ["user_id", "gmail_message_id"])
    op.create_index("idx_balance_user_time", "balance_snapshots", ["user_id", "observed_at"])

    # -- transactions --
    op.create_table(
        "transactions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("merchant", sa.Text, nullable=True),
        sa.Column("card_last_four", sa.String(4), nullable=True),
        sa.Column("purchase_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gmail_message_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_transaction_user_gmail", "transactions", ["user_id", "gmail_message_id"])
    op.create_index("idx_transactions_user_date", "transactions", ["user_id", "purchase_date"])

    # -- gmail_subscriptions --
    op.create_table(
        "gmail_subscriptions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("gmail_address", sa.String(255), nullable=False),
        sa.Column("history_id", sa.String(64), nullable=True),
        sa.Column("watch_expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("gmail_subscriptions")
    op.drop_table("transactions")
    op.drop_table("balance_snapshots")
    op.drop_table("commitments")
    op.drop_table("users")
