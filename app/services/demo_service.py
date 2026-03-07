"""Demo mode: create/reset a sandboxed demo user with seed data.

Each visitor who hits /api/auth/demo-start gets an isolated demo user
with realistic financial data pre-loaded. The data tells a "slightly
stressed" story -- enough income but tight margins, one dip window,
a couple subscriptions worth questioning.
"""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import BalanceSnapshot, Commitment, Transaction, User

logger = logging.getLogger(__name__)

DEMO_DISCORD_ID = "demo_000000000000"
DEMO_USERNAME = "demo"
DEMO_DISPLAY_NAME = "Demo User"

# Starting balance that produces a yellow/tight shield gauge.
DEMO_BALANCE = Decimal("2847.50")


async def get_or_create_demo_user(db: AsyncSession) -> User:
    """Find or insert the demo user row."""
    result = await db.execute(
        select(User).where(User.discord_id == DEMO_DISCORD_ID)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            discord_id=DEMO_DISCORD_ID,
            discord_username=DEMO_USERNAME,
            display_name=DEMO_DISPLAY_NAME,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        logger.info("Created demo user id=%s", user.id)

    return user


async def reset_demo_data(db: AsyncSession, user_id: int) -> None:
    """Wipe all existing demo data and re-seed from scratch."""
    await db.execute(delete(Transaction).where(Transaction.user_id == user_id))
    await db.execute(delete(BalanceSnapshot).where(BalanceSnapshot.user_id == user_id))
    await db.execute(delete(Commitment).where(Commitment.user_id == user_id))

    # Seed balance snapshot.
    db.add(BalanceSnapshot(
        user_id=user_id,
        balance=DEMO_BALANCE,
        observed_at=datetime.now(UTC),
        source="manual",
        account_label="checking",
    ))

    # Seed commitments.
    today = date.today()
    for spec in _seed_commitments(today):
        db.add(Commitment(user_id=user_id, **spec))

    await db.flush()
    logger.info("Demo data seeded for user_id=%s", user_id)


def _seed_commitments(today: date) -> list[dict]:
    """Build a list of commitment field dicts for the demo user.

    Data tells a story:
    - Biweekly paycheck (~$3,700 gross -> net)
    - Rent is the big one ($2,100)
    - Student loans, insurance, utilities eat another chunk
    - A handful of subscriptions (one or two feel wasteful)
    - Net monthly is positive but tight -- shield gauge shows yellow
    """
    return [
        # -- Income --
        {
            "name": "Paycheck (biweekly)",
            "amount": Decimal("3700.00"),
            "frequency": "biweekly",
            "anchor_date": _prior_friday(today),
            "start_date": today.replace(day=1),
            "is_paycheck": True,
            "is_active": True,
        },
        # -- Housing --
        {
            "name": "Rent",
            "amount": Decimal("-2100.00"),
            "frequency": "monthly",
            "day_of_month": 1,
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        # -- Debt --
        {
            "name": "Student Loan",
            "amount": Decimal("-324.00"),
            "frequency": "monthly",
            "day_of_month": 15,
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        # -- Insurance --
        {
            "name": "Auto Insurance",
            "amount": Decimal("-184.00"),
            "frequency": "day_interval",
            "interval_days": 30,
            "anchor_date": today.replace(day=10),
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        # -- Utilities --
        {
            "name": "Electric (DirectPay)",
            "amount": Decimal("-145.00"),
            "frequency": "monthly",
            "day_of_month": 20,
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        {
            "name": "Internet",
            "amount": Decimal("-83.00"),
            "frequency": "monthly",
            "day_of_month": 5,
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        {
            "name": "Gas Bill",
            "amount": Decimal("-42.00"),
            "frequency": "day_interval",
            "interval_days": 32,
            "anchor_date": today.replace(day=3),
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        {
            "name": "Phone Plan",
            "amount": Decimal("-55.00"),
            "frequency": "monthly",
            "day_of_month": 12,
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        # -- Essentials --
        {
            "name": "Groceries (weekly)",
            "amount": Decimal("-120.00"),
            "frequency": "weekly",
            "anchor_date": _prior_sunday(today),
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        {
            "name": "Gas (car, biweekly)",
            "amount": Decimal("-65.00"),
            "frequency": "biweekly",
            "anchor_date": _prior_friday(today),
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        {
            "name": "Cat Food (monthly)",
            "amount": Decimal("-48.00"),
            "frequency": "day_interval",
            "interval_days": 28,
            "anchor_date": today.replace(day=7),
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        # -- Subscriptions (some feel wasteful) --
        {
            "name": "Spotify",
            "amount": Decimal("-12.00"),
            "frequency": "monthly",
            "day_of_month": 8,
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        {
            "name": "ChatGPT Plus",
            "amount": Decimal("-20.00"),
            "frequency": "monthly",
            "day_of_month": 18,
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        {
            "name": "Adobe Creative Cloud",
            "amount": Decimal("-60.00"),
            "frequency": "monthly",
            "day_of_month": 22,
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        {
            "name": "GitHub Pro",
            "amount": Decimal("-4.00"),
            "frequency": "monthly",
            "day_of_month": 25,
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        {
            "name": "iCloud+",
            "amount": Decimal("-3.00"),
            "frequency": "monthly",
            "day_of_month": 2,
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        {
            "name": "Gym Membership",
            "amount": Decimal("-35.00"),
            "frequency": "monthly",
            "day_of_month": 1,
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
        {
            "name": "Renters Insurance",
            "amount": Decimal("-18.00"),
            "frequency": "monthly",
            "day_of_month": 1,
            "start_date": today.replace(day=1),
            "is_paycheck": False,
            "is_active": True,
        },
    ]


def _prior_friday(ref: date) -> date:
    """Return the most recent Friday on or before ref."""
    # Monday=0, Friday=4.
    days_since = (ref.weekday() - 4) % 7
    return date.fromordinal(ref.toordinal() - days_since)


def _prior_sunday(ref: date) -> date:
    """Return the most recent Sunday on or before ref."""
    # Monday=0, Sunday=6.
    days_since = (ref.weekday() - 6) % 7
    return date.fromordinal(ref.toordinal() - days_since)
