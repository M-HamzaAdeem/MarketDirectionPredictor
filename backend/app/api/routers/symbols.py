"""Configured symbols. Read-only and public — it exposes only static
configuration, not market or account data."""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/symbols", tags=["symbols"])


@router.get("")
def list_symbols() -> list[str]:
    return [symbol.value for symbol in get_settings().symbols]
