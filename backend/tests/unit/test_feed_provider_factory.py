import pytest

from app.core.config import Settings
from app.core.constants import FeedProvider
from app.feeds.factory import create_provider
from app.feeds.fallback_provider import FallbackMarketDataProvider
from app.feeds.mock_provider import MockMarketDataProvider
from app.feeds.twelve_data_provider import TwelveDataProvider


def test_creates_mock_provider_by_default() -> None:
    provider = create_provider(Settings())
    assert isinstance(provider, MockMarketDataProvider)


def test_creates_twelve_data_provider_wrapped_in_a_fallback_chain() -> None:
    settings = Settings(feed_provider=FeedProvider.TWELVE_DATA, twelve_data_api_key="test-key")
    provider = create_provider(settings)
    assert isinstance(provider, FallbackMarketDataProvider)
    # Reaching into the "private" provider list is test-only introspection
    # of the factory's wiring order, not something FallbackMarketDataProvider
    # promises as a public API.
    assert isinstance(provider._providers[0], TwelveDataProvider)
    assert isinstance(provider._providers[1], MockMarketDataProvider)


def test_twelve_data_without_an_api_key_raises() -> None:
    # Explicit empty string, not just omitted — Settings also reads
    # backend/.env, which may have a real key configured for manual runs.
    settings = Settings(feed_provider=FeedProvider.TWELVE_DATA, twelve_data_api_key="")
    with pytest.raises(ValueError, match="twelve_data_api_key"):
        create_provider(settings)
