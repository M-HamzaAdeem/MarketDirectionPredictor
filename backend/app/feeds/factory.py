"""Selects and constructs the configured MarketDataProvider.

The only place that branches on `Settings.feed_provider` — main.py depends
on this factory, not on any concrete provider class, so adding a new
provider means adding one branch here, not touching composition-root
wiring or scattering the choice across call sites.

`twelve_data` is returned bare, with no automatic fallback to the mock
feed on failure — a real feed failure must be loud and visible, not
silently substituted with synthetic data written into the same candles
table as real history (see [[remove-mock-auto-fallback]] in
decisions.md for the incident that prompted removing the earlier
fallback-chain wrapper). `mock` remains available as an explicit,
deliberate choice for local development and tests without hitting the
real API."""

from app.core.config import Settings
from app.core.constants import FeedProvider
from app.feeds.base import MarketDataProvider
from app.feeds.mock_provider import MockMarketDataProvider
from app.feeds.twelve_data_provider import TwelveDataProvider


def create_provider(settings: Settings) -> MarketDataProvider:
    if settings.feed_provider == FeedProvider.MOCK:
        return MockMarketDataProvider(time_acceleration=settings.mock_time_acceleration)

    if settings.feed_provider == FeedProvider.TWELVE_DATA:
        if not settings.twelve_data_api_key:
            raise ValueError("feed_provider is 'twelve_data' but twelve_data_api_key is not set")
        return TwelveDataProvider(api_key=settings.twelve_data_api_key)

    raise ValueError(f"Unknown feed_provider: {settings.feed_provider!r}")
