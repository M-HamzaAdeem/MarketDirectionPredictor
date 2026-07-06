"""Liveness/readiness endpoint. No auth required — it exposes no data,
only confirming the process is up, so it is intentionally public."""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def get_health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "environment": settings.app_env}
