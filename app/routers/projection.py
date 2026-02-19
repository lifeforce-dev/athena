from __future__ import annotations

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.schemas import ProjectionResponse, ScenarioRequest
from app.services.projection_service import ProjectionConfigError, build_projection, build_scenario_projection

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/projection', tags=['projection'])


@router.get('', response_model=ProjectionResponse)
async def get_projection(
    settings: Annotated[Settings, Depends(get_settings)],
    user_id: Annotated[int, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db)],
    as_of: date = Query(..., description='Target date (YYYY-MM-DD)'),
    from_date: date | None = Query(None, description='Start date (YYYY-MM-DD)'),
) -> ProjectionResponse:
    """Return a cash-flow projection for the requested date window."""
    logger.info(f'Projection requested. as_of={as_of} from_date={from_date}')
    try:
        return await build_projection(
            settings.config_path,
            as_of,
            from_date,
            db=db,
            user_id=user_id,
        )
    except ProjectionConfigError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


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
    try:
        return await build_scenario_projection(
            as_of=body.as_of,
            from_date=body.from_date,
            excluded_ids=body.excluded_ids,
            amount_overrides=body.amount_overrides,
            db=db,
            user_id=user_id,
        )
    except ProjectionConfigError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
