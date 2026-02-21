"""Athena dev-tools plugin.

This package is only installed in development environments. It registers
additional API routes (account reset, dev status) via the ``athena.plugins``
entry-point group. In production, this package is simply not installed, so
the endpoints do not exist -- there is no code to exploit.
"""
from __future__ import annotations

from fastapi import APIRouter

from athena_dev_tools.router import router as dev_router


def get_routers() -> list[APIRouter]:
    """Entry-point callable: return routers to register on the app."""
    return [dev_router]
