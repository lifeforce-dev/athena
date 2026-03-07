"""Pydantic models for the Teller bank integration.

Contains request/response schemas for API endpoints and internal models
that represent Teller API response shapes.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Request schemas (frontend → backend)
# ---------------------------------------------------------------------------


class TellerEnrollRequest(BaseModel):
    """Payload sent by the frontend after a successful Teller Connect flow."""

    access_token: str
    enrollment_id: str
    institution: str


class TellerSelectAccountRequest(BaseModel):
    """Payload sent by the frontend when the user picks a bank account."""

    account_id: str


# ---------------------------------------------------------------------------
# Response schemas (backend → frontend)
# ---------------------------------------------------------------------------


class TellerAccountOption(BaseModel):
    """A bank account choice presented to the user after enrollment."""

    id: str
    name: str
    type: str
    subtype: str
    currency: str
    institution_name: str


class TellerEnrollResponse(BaseModel):
    """Returned by POST /enroll with available accounts for user selection."""

    status: str  # TellerStatus value
    institution_name: str
    accounts: list[TellerAccountOption]


class TellerStatusResponse(BaseModel):
    """Current Teller connection state for the authenticated user."""

    is_connected: bool
    institution_name: str | None = None
    account_name: str | None = None
    last_synced_at: datetime | None = None
    status: str  # TellerStatus value


# ---------------------------------------------------------------------------
# Internal models (Teller API response shapes)
# ---------------------------------------------------------------------------


class TellerInstitution(BaseModel):
    """An institution as returned by the Teller API."""

    id: str
    name: str


class TellerAccount(BaseModel):
    """A bank account as returned by the Teller API."""

    id: str
    name: str
    type: str
    subtype: str
    currency: str
    institution: TellerInstitution


class TellerBalance(BaseModel):
    """Account balance as returned by the Teller API.

    Teller returns monetary amounts as strings.
    """

    account_id: str
    available: str
    ledger: str


class TellerTransaction(BaseModel):
    """A single transaction as returned by the Teller API.

    Amount parsing convention:
      Teller: negative = debit, positive = credit.
      Our DB: positive = money spent (matching existing BofA email convention).
      On ingest: abs(Decimal(amount)).quantize(Decimal("0.01")).
    """

    id: str
    account_id: str
    amount: str
    date: str
    description: str
    category: str | None = None
    status: str
    type: str
