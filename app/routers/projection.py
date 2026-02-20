from __future__ import annotations

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.schemas import ProjectionResponse, ScenarioRequest
from app.services.currency_service import get_user_currencies, to_account_currency
from app.services.projection_service import build_projection, build_scenario_projection

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/projection', tags=['projection'])


@router.get('', response_model=ProjectionResponse)
async def get_projection(
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    as_of: date = Query(..., description='Target date (YYYY-MM-DD)'),
    from_date: date | None = Query(None, description='Start date (YYYY-MM-DD)'),
) -> ProjectionResponse:
    """Return a cash-flow projection for the requested date window."""
    logger.info(f'Projection requested. as_of={as_of} from_date={from_date}')
    return await build_projection(
        as_of,
        from_date,
        db=db,
        user_id=user_id,
    )


@router.post('/scenario', response_model=ProjectionResponse)
async def run_scenario(
    body: ScenarioRequest,
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectionResponse:
    """Run a what-if scenario projection with commitment overrides."""
    logger.info(
        f'Scenario requested. as_of={body.as_of} from_date={body.from_date} '
        f'excluded={len(body.excluded_ids)} overrides={len(body.amount_overrides)}'
    )
    # Convert override amounts from display currency to account currency.
    if body.amount_overrides:
        info = await get_user_currencies(user_id, db)
        body.amount_overrides = {
            cid: await to_account_currency(amt, info)
            for cid, amt in body.amount_overrides.items()
        }
    return await build_scenario_projection(
        as_of=body.as_of,
        from_date=body.from_date,
        excluded_ids=body.excluded_ids,
        amount_overrides=body.amount_overrides,
        db=db,
        user_id=user_id,
    )
