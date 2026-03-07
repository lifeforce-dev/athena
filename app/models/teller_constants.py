"""Constants for Teller enrollment statuses.

Central source of truth for the status strings stored in the
``teller_enrollments.status`` column. Referenced by ORM model,
repository, router, and schema modules.
"""
from __future__ import annotations

from enum import StrEnum


class TellerStatus(StrEnum):
    """Valid values for TellerEnrollment.status."""

    AWAITING_ACCOUNT = "awaiting_account"
    SYNCING = "syncing"
    ACTIVE = "active"
    DISCONNECTED = "disconnected"
    ERROR = "error"


# Convenience sets for common filters.
CONNECTED_STATUSES = frozenset({
    TellerStatus.AWAITING_ACCOUNT,
    TellerStatus.ACTIVE,
    TellerStatus.SYNCING,
})

LIVE_STATUSES = frozenset({
    TellerStatus.ACTIVE,
    TellerStatus.SYNCING,
})
