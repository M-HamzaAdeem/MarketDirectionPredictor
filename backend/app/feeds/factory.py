"""Selects and constructs the configured MarketDataProvider.

The only place that branches on `Settings.feed_provider` — main.py depends
on this factory, not on any concrete provider class, so adding a new
provider means adding one branch here, not touching composition-root
wiring or scattering the choice across call sites.

Any real (non-mock) provider is wrapped in a `FallbackMarketDataProvider`
falling back to the mock feed — PROJECT.md requires a "safe fallback if
live feed is unavailable," and the mock feed is always available since it
has no external dependency."""

from app.core.config import Settings
from app.core.constants import FeedProvider
from app.feeds.base import MarketDataProvider
from app.feeds.fallback_provider import FallbackMarketDataProvider
from app.feeds.mock_provider import MockMarketDataProvider
from app.feeds.twelve_data_provider import TwelveDataProvider


def create_provider(settings: Settings) -> MarketDataProvider:
    if settings.feed_provider == FeedProvider.MOCK:
        return MockMarketDataProvider(time_acceleration=settings.mock_time_acceleration)

    if settings.feed_provider == FeedProvider.TWELVE_DATA:
        if not settings.twelve_data_api_key:
            raise ValueError("feed_provider is 'twelve_data' but twelve_data_api_key is not set")
        primary = TwelveDataProvider(api_key=settings.twelve_data_api_key)
        fallback = MockMarketDataProvider(time_acceleration=settings.mock_time_acceleration)
        return FallbackMarketDataProvider([primary, fallback])

    raise ValueError(f"Unknown feed_provider: {settings.feed_provider!r}")
