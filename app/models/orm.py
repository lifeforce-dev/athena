"""SQLAlchemy ORM models for the Athena database schema."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    discord_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    discord_username: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128))
    account_currency: Mapped[str | None] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("idx_users_discord_id", "discord_id"),)


class Commitment(Base):
    """Recurring expenses, income, and one-time payments.

    Uses signed amounts (negative = expense) and flat columns for recurrence,
    unlike the domain model which uses a discriminated union. The repository
    layer handles bidirectional conversion.
    """

    __tablename__ = "commitments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Signed amount: negative = expense, positive = income.
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Recurrence type: 'weekly', 'biweekly', 'monthly', 'day_interval', 'once'.
    frequency: Mapped[str] = mapped_column(String(32), nullable=False)
    day_of_month: Mapped[int | None] = mapped_column()
    interval_days: Mapped[int | None] = mapped_column()
    anchor_date: Mapped[date | None] = mapped_column(Date)
    one_time_date: Mapped[date | None] = mapped_column(Date)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_paycheck: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_commitments_user_id", "user_id"),
        Index("idx_commitments_user_active", "user_id", "is_active"),
    )


class BalanceSnapshot(Base):
    """Real-time balance observations from bank notification emails."""

    __tablename__ = "balance_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    account_label: Mapped[str | None] = mapped_column(String(64))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="gmail")
    gmail_message_id: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # NULL gmail_message_id values intentionally bypass the uniqueness constraint,
    # allowing multiple manually-entered records per user. PostgreSQL treats NULLs
    # as distinct in UNIQUE constraints.
    __table_args__ = (
        UniqueConstraint("user_id", "gmail_message_id", name="uq_balance_user_gmail"),
        Index("idx_balance_user_time", "user_id", "observed_at"),
    )


class Transaction(Base):
    """Debit card usage notifications from bank emails."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    merchant: Mapped[str | None] = mapped_column(Text)
    card_last_four: Mapped[str | None] = mapped_column(String(4))
    purchase_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    gmail_message_id: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # NULL gmail_message_id values intentionally bypass the uniqueness constraint,
    # allowing multiple manually-entered records per user. PostgreSQL treats NULLs
    # as distinct in UNIQUE constraints.
    __table_args__ = (
        UniqueConstraint("user_id", "gmail_message_id", name="uq_transaction_user_gmail"),
        Index("idx_transactions_user_date", "user_id", "purchase_date"),
    )


class GmailSubscription(Base):
    """Tracks Gmail push notification watch state per user."""

    __tablename__ = "gmail_subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    gmail_address: Mapped[str] = mapped_column(String(255), nullable=False)
    history_id: Mapped[str | None] = mapped_column(String(64))
    watch_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
