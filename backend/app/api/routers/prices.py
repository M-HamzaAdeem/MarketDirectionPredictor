"""Latest tick price per configured symbol, from the in-memory feed cache."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_feed_service
from app.core.config import get_settings
from app.schemas.price import PriceOut
from app.services.feed_service import FeedService

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("", response_model=list[PriceOut])
def get_latest_prices(feed_service: FeedService = Depends(get_feed_service)) -> list[PriceOut]:
    prices: list[PriceOut] = []
    for symbol in get_settings().symbols:
        tick = feed_service.latest_price(symbol)
        if tick is not None:
            prices.append(PriceOut(symbol=tick.symbol, price=tick.price, timestamp=tick.timestamp))
    return prices
