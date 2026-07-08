"""Latest price per configured symbol: the live in-memory tick cache when
available, falling back to the most recent closed 1m candle otherwise.

A lower-liquidity pair (e.g. AUDUSD) can go a while without a single live
tick even though its candles are already populated from backfill/earlier
ticks — without this fallback, its price card would stay blank ("—")
indefinitely rather than showing the best data actually available."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_feed_service
from app.core.config import get_settings
from app.core.constants import Timeframe
from app.schemas.price import PriceOut
from app.services.feed_service import FeedService
from app.storage.database import get_session
from app.storage.repositories.candle_repository import CandleRepository

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("", response_model=list[PriceOut])
async def get_latest_prices(
    feed_service: FeedService = Depends(get_feed_service),
    session: AsyncSession = Depends(get_session),
) -> list[PriceOut]:
    candle_repository = CandleRepository(session)
    prices: list[PriceOut] = []

    for symbol in get_settings().symbols:
        tick = feed_service.latest_price(symbol)
        if tick is not None:
            prices.append(PriceOut(symbol=tick.symbol, price=tick.price, timestamp=tick.timestamp))
            continue

        candle = await candle_repository.get_latest(symbol, Timeframe.M1)
        if candle is not None:
            prices.append(PriceOut(symbol=symbol, price=candle.close, timestamp=candle.close_time))

    return prices
