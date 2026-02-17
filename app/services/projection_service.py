from __future__ import annotations

import asyncio
import logging
from json import JSONDecodeError
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from app.core.post_processing import process_ledger
from app.core.projection import project_cash_on
from app.models.domain import CashFlowConfig, TemplateTag
from app.models.schemas import ProjectionResponse

logger = logging.getLogger(__name__)


class ProjectionConfigError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


async def build_projection(config_path: Path, as_of: date, from_date: date | None) -> ProjectionResponse:
    """Build a full projection with month and pay-period summaries."""
    try:
        raw = await asyncio.to_thread(config_path.read_text, encoding='utf-8')
        cfg = CashFlowConfig.from_json(raw)
    except FileNotFoundError as exc:
        logger.exception(
            f'Projection config file not found. config_path={config_path} as_of={as_of} from_date={from_date}'
        )
        raise ProjectionConfigError(status_code=404, detail='Projection config file not found') from exc
    except JSONDecodeError as exc:
        logger.exception(
            f'Projection config is not valid JSON. config_path={config_path} as_of={as_of} from_date={from_date}'
        )
        raise ProjectionConfigError(status_code=422, detail='Projection config is not valid JSON') from exc
    except ValidationError as exc:
        logger.exception(
            f'Projection config does not match schema. config_path={config_path} as_of={as_of} from_date={from_date}'
        )
        raise ProjectionConfigError(status_code=422, detail='Projection config does not match schema') from exc

    if from_date is None:
        from_date = date.today()

    ending, raw_ledger = project_cash_on(
        initial_balance=cfg.initial_balance,
        templates=cfg.templates,
        as_of=as_of,
        from_date=from_date,
    )

    window_start = min(from_date, as_of)
    window_end = max(from_date, as_of)

    paycheck_names = {t.name for t in cfg.templates if TemplateTag.PAYCHECK in t.tags}
    processed = process_ledger(raw_ledger, cfg.initial_balance, window_start, window_end, paycheck_names)

    logger.info(
        f'Projection built. entries={len(processed.ledger)} '
        f'months={len(processed.months)} pay_periods={len(processed.pay_periods)}'
    )

    return ProjectionResponse(
        as_of=as_of,
        from_date=from_date,
        current_balance=ending,
        ledger=processed.ledger,
        months=processed.months,
        pay_periods=processed.pay_periods,
    )
