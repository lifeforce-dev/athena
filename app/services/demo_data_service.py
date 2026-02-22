"""Generate demo data in-memory for overlay previews.

Uses the same seed specifications from demo_service, but runs them through
the projection engine without writing anything to the database. Returns
typed response objects that the demo endpoints can serialize directly.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from app.core.post_processing import process_ledger
from app.core.projection import project_cash_on
from app.models.commitment_schemas import CommitmentResponse
from app.models.domain import CashFlowTemplate, Direction, TemplateTag
from app.models.schemas import ProjectionResponse
from app.repositories.commitment_repository import _build_recurrence
from app.services.demo_service import DEMO_BALANCE, _seed_commitments

logger = logging.getLogger(__name__)


def _spec_to_template(spec: dict, today: date) -> CashFlowTemplate:
    """Convert a raw seed spec dict into a CashFlowTemplate."""
    raw_amount = spec["amount"]
    amount = abs(raw_amount)
    direction = Direction.INFLOW if raw_amount > 0 else Direction.OUTFLOW
    tags = [TemplateTag.PAYCHECK] if spec.get("is_paycheck") else []

    # Build a minimal object with the fields _build_recurrence expects.
    class _FakeRow:
        pass

    row = _FakeRow()
    row.id = 0  # type: ignore[attr-defined]
    row.frequency = spec["frequency"]  # type: ignore[attr-defined]
    row.anchor_date = spec.get("anchor_date")  # type: ignore[attr-defined]
    row.start_date = spec.get("start_date", today)  # type: ignore[attr-defined]
    row.day_of_month = spec.get("day_of_month")  # type: ignore[attr-defined]
    row.interval_days = spec.get("interval_days")  # type: ignore[attr-defined]
    row.one_time_date = spec.get("one_time_date")  # type: ignore[attr-defined]

    recurrence = _build_recurrence(row)  # type: ignore[arg-type]

    start = spec.get("start_date", today)
    if spec["frequency"] == "once" and spec.get("one_time_date"):
        start = spec["one_time_date"]

    return CashFlowTemplate(
        name=spec["name"],
        amount=amount,
        direction=direction,
        recurrence=recurrence,
        start_date=start,
        end_date=spec.get("end_date"),
        tags=tags,
    )


def _spec_to_commitment_response(spec: dict, idx: int) -> CommitmentResponse:
    """Convert a raw seed spec dict into a CommitmentResponse."""
    now = datetime.now(timezone.utc)
    return CommitmentResponse(
        id=idx + 1,
        name=spec["name"],
        amount=spec["amount"],
        frequency=spec["frequency"],
        day_of_month=spec.get("day_of_month"),
        interval_days=spec.get("interval_days"),
        anchor_date=spec.get("anchor_date"),
        one_time_date=spec.get("one_time_date"),
        start_date=spec.get("start_date", date.today()),
        end_date=spec.get("end_date"),
        is_paycheck=spec.get("is_paycheck", False),
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def build_demo_projection(today: date | None = None) -> ProjectionResponse:
    """Build a 90-day projection using demo seed data (no DB)."""
    today = today or date.today()
    from_date = today
    as_of = today + timedelta(days=90)

    specs = _seed_commitments(today)
    templates = [_spec_to_template(s, today) for s in specs]
    logger.info(
        "[TourDebug][demo_data_service] building projection today=%s templates=%s",
        today,
        len(templates),
    )

    _, raw_ledger = project_cash_on(
        initial_balance=DEMO_BALANCE,
        templates=templates,
        as_of=as_of,
        from_date=from_date,
    )

    paycheck_names = {t.name for t in templates if TemplateTag.PAYCHECK in t.tags}
    processed = process_ledger(raw_ledger, DEMO_BALANCE, from_date, as_of, paycheck_names)

    logger.info(
        "[TourDebug][demo_data_service] projection ready ledger=%s months=%s pay_periods=%s",
        len(processed.ledger),
        len(processed.months),
        len(processed.pay_periods),
    )

    return ProjectionResponse(
        as_of=as_of,
        from_date=from_date,
        current_balance=DEMO_BALANCE,
        has_initial_balance=True,
        ledger=processed.ledger,
        months=processed.months,
        pay_periods=processed.pay_periods,
    )


def build_demo_commitments(today: date | None = None) -> list[CommitmentResponse]:
    """Return the demo seed commitments as API response objects (no DB)."""
    today = today or date.today()
    specs = _seed_commitments(today)
    result = [_spec_to_commitment_response(s, i) for i, s in enumerate(specs)]
    logger.info(
        "[TourDebug][demo_data_service] commitments ready today=%s count=%s",
        today,
        len(result),
    )
    return result
