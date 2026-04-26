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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.teller_constants import CONNECTED_STATUSES, TellerStatus


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    discord_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    discord_username: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128))
    account_currency: Mapped[str | None] = mapped_column(String(3))
    display_currency: Mapped[str | None] = mapped_column(String(3))
    account_language: Mapped[str | None] = mapped_column(String(5))
    completed_tours: Mapped[str | None] = mapped_column(Text)
    dismissed_modals: Mapped[str | None] = mapped_column(Text)

    # Dollar-based risk thresholds for the dashboard verdict (Critical / Tight /
    # Comfortable). The lowest projected balance over the window is compared to
    # these to pick a label.
    risk_critical_threshold: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("500.00")
    )
    risk_tight_threshold: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default=text("1000.00")
    )

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
    """Balance observations from Teller bank integration."""

    __tablename__ = "balance_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    account_label: Mapped[str | None] = mapped_column(String(64))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="teller")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_balance_user_time", "user_id", "observed_at"),
    )


class Transaction(Base):
    """Bank transactions from Teller integration."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    merchant: Mapped[str | None] = mapped_column(Text)
    card_last_four: Mapped[str | None] = mapped_column(String(4))
    purchase_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default="teller")
    teller_transaction_id: Mapped[str | None] = mapped_column(String(128))
    category: Mapped[str | None] = mapped_column(String(128))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "teller_transaction_id", name="uq_transaction_user_teller"),
        Index("idx_transactions_user_date", "user_id", "purchase_date"),
    )


class TellerEnrollment(Base):
    """Tracks a user's Teller bank enrollment and connection status.

    Single active enrollment per user, enforced by a partial unique index.
    Disconnected/error rows are preserved for history.
    """

    __tablename__ = "teller_enrollments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    enrollment_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Fernet-encrypted access token. Decrypted only when making API calls.
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)

    # The single checking account we track (populated by Phase 2 background sync).
    account_id: Mapped[str | None] = mapped_column(String(128))
    account_name: Mapped[str | None] = mapped_column(String(255))
    account_currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="USD")

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=TellerStatus.AWAITING_ACCOUNT
    )

    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_manual_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_teller_enrollment_user", "user_id"),
        # Partial unique index: only one active enrollment per user.
        # Disconnected/error rows don't block re-enrollment.
        Index(
            "uq_teller_user_active",
            "user_id",
            unique=True,
            postgresql_where=text(
                f"status IN ({', '.join(repr(str(s)) for s in CONNECTED_STATUSES)})"
            ),
        ),
    )
