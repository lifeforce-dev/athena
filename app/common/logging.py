"""Centralized logging configuration for Athena."""
from __future__ import annotations

import logging


_LOG_FORMAT = '%(levelname)s %(asctime)s [%(module)s] %(message)s (%(pathname)s:%(lineno)d)'
_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
_initialized: bool = False


def setup_logging(log_level: int = logging.INFO) -> None:
    """Configure the root logger with a consistent format and level.

    Call once at each entrypoint (FastAPI startup, CLI main) before any
    logging calls. Subsequent calls are silently ignored so that library
    imports cannot double-configure the logger.

    Args:
        log_level: Minimum severity to emit. Defaults to INFO.
    """
    global _initialized

    if _initialized:
        return

    # Clear any handlers that may have been attached by library imports
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    logging.basicConfig(level=log_level, format=_LOG_FORMAT, datefmt=_DATE_FORMAT)
    _initialized = True
