"""FastAPI application entrypoint.

Assembly is done through create_app() rather than module-level side effects,
so tests can build an app instance with different settings without relying
on process-wide state.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import candles, health, predictions, prices, symbols
from app.core.config import get_settings
from app.feeds.mock_provider import MockMarketDataProvider
from app.services.feed_service import FeedService
from app.storage.database import init_models


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await init_models()

    feed_service = FeedService(MockMarketDataProvider(), settings)
    app.state.feed_service = feed_service
    await feed_service.start()

    try:
        yield
    finally:
        await feed_service.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Market Direction Predictor", version="0.1.0", lifespan=_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(symbols.router)
    app.include_router(prices.router)
    app.include_router(candles.router)
    app.include_router(predictions.router)
    return app


app = create_app()
