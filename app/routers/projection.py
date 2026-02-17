from __future__ import annotations

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.dependencies import get_current_user
from app.models.schemas import ProjectionResponse
from app.services.projection_service import ProjectionConfigError, build_projection

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/projection', tags=['projection'])


@router.get('', response_model=ProjectionResponse)
async def get_projection(
    settings: Annotated[Settings, Depends(get_settings)],
    _user: Annotated[dict, Depends(get_current_user)],
    as_of: date = Query(..., description='Target date (YYYY-MM-DD)'),
    from_date: date | None = Query(None, description='Start date (YYYY-MM-DD)'),
) -> ProjectionResponse:
    """Return a cash-flow projection for the requested date window."""
    logger.info(f'Projection requested. as_of={as_of} from_date={from_date}')
    try:
        return await build_projection(settings.config_path, as_of, from_date)
    except ProjectionConfigError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
