"""FastAPI application entrypoint.

Assembly is done through create_app() rather than module-level side effects,
so tests can build an app instance with different settings without relying
on process-wide state.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.dependencies import get_prediction_engine
from app.api.routers import backtests, candles, config, health, predictions, prices, signals, symbols, websocket
from app.core.config import get_settings
from app.core.constants import DataSource
from app.core.security_headers import add_security_headers
from app.feeds.factory import create_provider
from app.feeds.tradingview_client import TradingViewClient
from app.services.broadcast_service import BroadcastService
from app.services.candle_close_handler import CandleCloseHandler
from app.services.connection_manager import ConnectionManager
from app.services.feed_service import FeedService
from app.services.prediction_service import PredictionService
from app.services.signal_service import SignalService
from app.services.signal_tracker import SignalTracker
from app.services.tradingview_feed_service import TradingViewFeedService
from app.storage.database import get_session_factory, init_models
from app.storage.models import (
    CandleColumns,
    CandleORM,
    PredictionColumns,
    PredictionORM,
    SignalColumns,
    SignalORM,
    TradingViewCandleORM,
    TradingViewPredictionORM,
    TradingViewSignalORM,
)


def _build_candle_close_handlers(
    broadcaster: BroadcastService,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    candle_model: type[CandleColumns] = CandleORM,
    prediction_model: type[PredictionColumns] = PredictionORM,
    signal_model: type[SignalColumns] = SignalORM,
) -> list[CandleCloseHandler]:
    """One pipeline's handler triad. Order matters: handlers run
    sequentially per candle (see FeedService._handle_closed_candle /
    CandleCloseHandler). SignalTracker must resolve existing OPEN signals
    before SignalService can create a new one from this same candle, or a
    signal could be opened and resolved against the very candle that
    triggered it — true for either pipeline, which is exactly why this is
    one function instead of two copies of the same three-line list."""
    return [
        PredictionService(
            get_prediction_engine(), broadcaster, session_factory, candle_model=candle_model,
            prediction_model=prediction_model,
        ),
        SignalTracker(session_factory, broadcaster, signal_model=signal_model),
        SignalService(broadcaster, session_factory, candle_model=candle_model, signal_model=signal_model),
    ]


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await init_models()

    session_factory = get_session_factory()
    broadcaster = BroadcastService(app.state.connection_manager, source=DataSource.TWELVE_DATA)

    feed_service = FeedService(
        create_provider(settings),
        settings,
        broadcaster,
        session_factory,
        _build_candle_close_handlers(broadcaster, session_factory),
    )
    app.state.feed_service = feed_service
    await feed_service.backfill()
    await feed_service.start()

    # A second, fully independent pipeline (own tables, own handler
    # instances) — on and the default source by default (see
    # Settings.tradingview_enabled), since it needs no API key; set to
    # False to run FEED_PROVIDER's pipeline only.
    app.state.tradingview_feed_service = None
    if settings.tradingview_enabled:
        tradingview_broadcaster = BroadcastService(app.state.connection_manager, source=DataSource.TRADINGVIEW)
        tradingview_feed_service = TradingViewFeedService(
            TradingViewClient(exchange=settings.tradingview_exchange),
            settings,
            tradingview_broadcaster,
            session_factory,
            _build_candle_close_handlers(
                tradingview_broadcaster,
                session_factory,
                candle_model=TradingViewCandleORM,
                prediction_model=TradingViewPredictionORM,
                signal_model=TradingViewSignalORM,
            ),
            poll_interval_seconds=settings.tradingview_poll_interval_seconds,
        )
        app.state.tradingview_feed_service = tradingview_feed_service
        await tradingview_feed_service.backfill()
        await tradingview_feed_service.start()

    try:
        yield
    finally:
        await feed_service.stop()
        if app.state.tradingview_feed_service is not None:
            await app.state.tradingview_feed_service.stop()


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
