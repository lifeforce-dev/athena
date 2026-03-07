"""Teller background synchronization tasks.

Houses the periodic balance sync, webhook-triggered balance refresh,
and stale enrollment recovery — all Teller-specific concerns that
don't belong in the application entry point.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.common.encryption import decrypt_token
from app.config import Settings
from app.repositories import balance_repository, teller_repository
from app.services.currency_service import convert_amount, get_user_account_currency
from app.services.teller_service import (
    TellerApiError,
    build_teller_client,
    fetch_balances,
)

logger = logging.getLogger(__name__)


async def sync_all_balances(
    factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    cert_path: str,
    key_path: str,
) -> None:
    """Fetch and store latest balance for all active Teller enrollments.

    Runs once per daily cycle. Each enrollment is handled independently so
    a single failure does not block the rest.
    """
    async with factory() as db:
        enrollments = await teller_repository.get_all_active(db)

    for enrollment in enrollments:
        try:
            token = decrypt_token(
                enrollment.access_token_encrypted, settings.teller_encryption_key
            )

            async with build_teller_client(cert_path, key_path, token) as client:
                balance_data = await fetch_balances(client, enrollment.account_id)  # type: ignore[arg-type]

            try:
                raw_balance = Decimal(balance_data.available).quantize(Decimal("0.01"))
            except (InvalidOperation, ValueError):
                raw_balance = Decimal("0.00")

            # Single DB session for currency lookup + balance write + sync timestamp.
            async with factory() as db:
                user_currency = await get_user_account_currency(enrollment.user_id, db)

                converted_balance = await convert_amount(
                    raw_balance, enrollment.account_currency, user_currency
                )

                now = datetime.now(UTC)
                await balance_repository.create_from_teller(
                    db,
                    user_id=enrollment.user_id,
                    balance=converted_balance,
                    observed_at=now,
                    account_label=enrollment.account_name,
                )
                await teller_repository.update_last_synced(db, enrollment.id)
                await db.commit()

            logger.info("Daily sync complete for enrollment %s", enrollment.id)

        except TellerApiError as exc:
            logger.warning(
                "Teller API error during daily sync (enrollment %s): %s",
                enrollment.id,
                exc.detail,
            )
            if exc.status_code in (401, 403):
                async with factory() as db:
                    await teller_repository.mark_disconnected(db, enrollment.id)
                    await db.commit()

        except Exception:
            logger.exception("Daily sync failed for enrollment %s", enrollment.id)


async def periodic_sync(
    factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    cert_path: str,
    key_path: str,
) -> None:
    """Background loop: sync Teller balances every 24 hours."""
    while True:
        await asyncio.sleep(24 * 3600)
        try:
            await sync_all_balances(factory, settings, cert_path, key_path)
        except Exception:
            logger.exception("Error in periodic Teller balance sync")


async def reconcile_stale_enrollments(
    factory: async_sessionmaker[AsyncSession],
) -> None:
    """Transition SYNCING enrollments to ERROR on startup.

    If the process crashed between committing SYNCING and the background
    task completing, these rows are stranded. There is no in-process task
    to finish the sync, so we mark them ERROR so the user can retry.
    """
    async with factory() as db:
        count = await teller_repository.reconcile_stale_syncing(db)
        await db.commit()
    if count:
        logger.warning(
            "Recovered %d enrollment(s) stranded in SYNCING → marked ERROR", count
        )
