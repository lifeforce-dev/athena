"""Business logic for commitment management."""
from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.projection import iter_occurrences
from app.models.commitment_schemas import (
    CommitmentCreate,
    CommitmentResponse,
    CommitmentUpdate,
)
from app.models.orm import Commitment
from app.repositories import commitment_repository as repo

# Frequency -> required field(s) mapping for merged-state validation.
_FREQUENCY_REQUIRED_FIELDS: dict[str, list[str]] = {
    "daily": ["anchor_date"],
    "weekly": ["anchor_date"],
    "biweekly": ["anchor_date"],
    "monthly": ["day_of_month"],
    "day_interval": ["anchor_date", "interval_days"],
    "once": ["one_time_date"],
}

# All frequency-specific date columns. When switching frequencies, columns
# not required by the new frequency are nulled out to prevent stale data.
_ALL_FREQUENCY_DATE_FIELDS = {"day_of_month", "interval_days", "anchor_date", "one_time_date"}


def _validate_merged_state(frequency: str, merged: dict[str, object]) -> None:
    """Ensure the merged commitment state has valid frequency-specific fields.

    Raises ValueError if required fields are missing for the frequency.
    """
    required = _FREQUENCY_REQUIRED_FIELDS.get(frequency, [])
    missing = [f for f in required if not merged.get(f)]

    if missing:
        raise ValueError(
            f"{', '.join(missing)} required for '{frequency}' frequency"
        )


async def list_commitments(db: AsyncSession, user_id: int) -> list[Commitment]:
    """Return all active commitments for a user."""
    return await repo.list_active(db, user_id)


async def get_commitment(
    db: AsyncSession,
    commitment_id: int,
    user_id: int,
) -> Commitment | None:
    """Get a single commitment by ID, scoped to user."""
    return await repo.get_by_id(db, commitment_id, user_id)


async def create_commitment(
    db: AsyncSession,
    user_id: int,
    data: CommitmentCreate,
) -> Commitment:
    """Create a new commitment from validated request data."""
    return await repo.create(db, user_id, **data.model_dump())


async def update_commitment(
    db: AsyncSession,
    commitment_id: int,
    user_id: int,
    data: CommitmentUpdate,
) -> Commitment | None:
    """Update a commitment with only the provided fields.

    Validates that the merged result (existing + delta) still has all
    required frequency-specific fields before persisting.
    """
    fields = data.model_dump(exclude_unset=True)
    if not fields:
        return await repo.get_by_id(db, commitment_id, user_id)

    existing = await repo.get_by_id(db, commitment_id, user_id)
    if existing is None:
        return None

    # Build merged view: existing column values overridden by update fields.
    merged: dict[str, object] = {
        "frequency": existing.frequency,
        "day_of_month": existing.day_of_month,
        "interval_days": existing.interval_days,
        "anchor_date": existing.anchor_date,
        "one_time_date": existing.one_time_date,
    }
    merged.update(fields)

    new_frequency = str(merged["frequency"])
    _validate_merged_state(new_frequency, merged)

    # When frequency changes, null out fields that no longer apply.
    if "frequency" in fields:
        required = set(_FREQUENCY_REQUIRED_FIELDS.get(new_frequency, []))
        stale = _ALL_FREQUENCY_DATE_FIELDS - required

        for field_name in stale:
            fields.setdefault(field_name, None)

    return await repo.apply_update(db, existing, **fields)


async def delete_commitment(
    db: AsyncSession,
    commitment_id: int,
    user_id: int,
) -> bool:
    """Soft-delete a commitment. Returns True if found and deactivated."""
    return await repo.soft_delete(db, commitment_id, user_id)


# How far ahead to search for the next occurrence.  Long enough to cover
# any sensible recurrence (yearly events, custom day_intervals up to ~360d)
# without burning cycles on infinite generators.
_NEXT_OCCURRENCE_HORIZON_DAYS = 400


def compute_next_occurrence(commitment: Commitment, today: date | None = None) -> date | None:
    """Return the first occurrence date on or after today, or None.

    None is returned when the commitment will never fire again — its
    ``end_date`` is in the past, it's a past one-time event, or no
    occurrence falls within the search horizon.
    """
    today = today or date.today()

    if commitment.end_date is not None and commitment.end_date < today:
        return None

    template = repo.to_domain(commitment)

    # Cap the search at end_date if set, otherwise a fixed horizon.
    horizon = today.fromordinal(today.toordinal() + _NEXT_OCCURRENCE_HORIZON_DAYS)
    limit = min(template.end_date, horizon) if template.end_date else horizon

    for occ in iter_occurrences(template, up_to=limit):
        if occ >= today:
            return occ

    return None


def build_response(commitment: Commitment, today: date | None = None) -> CommitmentResponse:
    """Build a CommitmentResponse with the computed next_occurrence field."""
    response = CommitmentResponse.model_validate(commitment)
    response.next_occurrence = compute_next_occurrence(commitment, today=today)
    return response
