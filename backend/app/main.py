"""FastAPI application entrypoint.

Assembly is done through create_app() rather than module-level side effects,
so tests can build an app instance with different settings without relying
on process-wide state.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import get_prediction_engine
from app.api.routers import backtests, candles, config, health, predictions, prices, signals, symbols, websocket
from app.core.config import get_settings
from app.core.security_headers import add_security_headers
from app.feeds.factory import create_provider
from app.services.broadcast_service import BroadcastService
from app.services.connection_manager import ConnectionManager
from app.services.feed_service import FeedService
from app.services.prediction_service import PredictionService
from app.services.signal_service import SignalService
from app.services.signal_tracker import SignalTracker
from app.storage.database import get_session_factory, init_models


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await init_models()

    session_factory = get_session_factory()
    broadcaster = BroadcastService(app.state.connection_manager)

    # Order matters: handlers run sequentially per candle (see
    # FeedService._handle_closed_candle / CandleCloseHandler). SignalTracker
    # must resolve existing OPEN signals before SignalService can create a
    # new one from this same candle, or a signal could be opened and
    # resolved against the very candle that triggered it.
    candle_close_handlers = [
        PredictionService(get_prediction_engine(), broadcaster, session_factory),
        SignalTracker(session_factory, broadcaster),
        SignalService(broadcaster, session_factory),
    ]

    feed_service = FeedService(
        create_provider(settings),
        settings,
        broadcaster,
        session_factory,
        candle_close_handlers,
    )
    app.state.feed_service = feed_service
    await feed_service.backfill()
    await feed_service.start()

    try:
        yield
    finally:
        await feed_service.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Market Direction Predictor", version="0.1.0", lifespan=_lifespan)
    app.state.connection_manager = ConnectionManager()

    app.middleware("http")(add_security_headers)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(symbols.router)
    app.include_router(prices.router)
    app.include_router(candles.router)
    app.include_router(predictions.router)
    app.include_router(signals.router)
    app.include_router(backtests.router)
    app.include_router(websocket.router)
    return app


app = create_app()
