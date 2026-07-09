"""Latest price per configured symbol: the live in-memory tick cache when
available, falling back to the most recent closed 1m candle otherwise.

A lower-liquidity pair (e.g. AUDUSD) can go a while without a single live
tick even though its candles are already populated from backfill/earlier
ticks — without this fallback, its price card would stay blank ("—")
indefinitely rather than showing the best data actually available.

Returns one source's prices per call (`?source=`, default twelve_data) —
the frontend only ever displays one source at a time, so there's no need
for a dual-source payload it would only half-use."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_feed_service, get_tradingview_feed_service
from app.api.source_models import candle_model_for
from app.core.config import get_settings
from app.core.constants import DataSource, Timeframe
from app.schemas.price import PriceOut
from app.services.feed_service import FeedService
from app.services.tradingview_feed_service import TradingViewFeedService
from app.storage.database import get_session
from app.storage.repositories.candle_repository import CandleRepository

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("", response_model=list[PriceOut])
async def get_latest_prices(
    source: DataSource = Query(default=DataSource.TWELVE_DATA),
    feed_service: FeedService = Depends(get_feed_service),
    tradingview_feed_service: TradingViewFeedService | None = Depends(get_tradingview_feed_service),
    session: AsyncSession = Depends(get_session),
) -> list[PriceOut]:
    if source == DataSource.TRADINGVIEW and tradingview_feed_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TradingView pipeline is not enabled (Settings.tradingview_enabled is False)",
        )

    live_source = tradingview_feed_service if source == DataSource.TRADINGVIEW else feed_service
    candle_repository = CandleRepository(session, model=candle_model_for(source))
    prices: list[PriceOut] = []

    for symbol in get_settings().symbols:
        tick = live_source.latest_price(symbol)
        if tick is not None:
            prices.append(PriceOut(symbol=tick.symbol, price=tick.price, timestamp=tick.timestamp))
            continue

        candle = await candle_repository.get_latest(symbol, Timeframe.M1)
        if candle is not None:
            prices.append(PriceOut(symbol=symbol, price=candle.close, timestamp=candle.close_time))

    return prices
