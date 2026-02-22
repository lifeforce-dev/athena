"""Public demo data endpoints for overlay previews.

These endpoints return pre-built sample data without authentication.
They power the demo overlay that appears on top of a new user's empty
dashboard, commitments, and simulation views during the guided tour.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from app.models.commitment_schemas import CommitmentResponse
from app.models.schemas import ProjectionResponse
from app.services.demo_data_service import build_demo_commitments, build_demo_projection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/dashboard", response_model=ProjectionResponse)
async def demo_dashboard() -> ProjectionResponse:
    """Return a demo projection for the dashboard overlay."""
    logger.info("[TourDebug][demo_data] GET /api/demo/dashboard")
    result = build_demo_projection()
    logger.info(
        "[TourDebug][demo_data] dashboard response built ledger=%s months=%s pay_periods=%s",
        len(result.ledger),
        len(result.months),
        len(result.pay_periods),
    )
    return result


@router.get("/commitments", response_model=list[CommitmentResponse])
async def demo_commitments() -> list[CommitmentResponse]:
    """Return demo commitments for the commitments overlay."""
    logger.info("[TourDebug][demo_data] GET /api/demo/commitments")
    result = build_demo_commitments()
    logger.info("[TourDebug][demo_data] commitments response built count=%s", len(result))
    return result


@router.get("/simulation", response_model=ProjectionResponse)
async def demo_simulation() -> ProjectionResponse:
    """Return a demo projection for the simulation overlay.

    Uses the same projection as the dashboard -- the frontend applies
    its own what-if toggles on top.
    """
    logger.info("[TourDebug][demo_data] GET /api/demo/simulation")
    result = build_demo_projection()
    logger.info(
        "[TourDebug][demo_data] simulation response built ledger=%s months=%s pay_periods=%s",
        len(result.ledger),
        len(result.months),
        len(result.pay_periods),
    )
    return result
