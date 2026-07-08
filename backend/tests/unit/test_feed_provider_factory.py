import pytest

from app.core.config import Settings
from app.core.constants import FeedProvider
from app.feeds.factory import create_provider
from app.feeds.mock_provider import MockMarketDataProvider
from app.feeds.twelve_data_provider import TwelveDataProvider


def test_creates_mock_provider_by_default() -> None:
    # _env_file=None bypasses the developer's real .env (which may set
    # FEED_PROVIDER=twelve_data for manual runs) so this purely tests the
    # field's declared default, not whatever's configured for local use.
    provider = create_provider(Settings(_env_file=None))
    assert isinstance(provider, MockMarketDataProvider)


def test_creates_a_bare_twelve_data_provider_with_no_fallback() -> None:
    settings = Settings(feed_provider=FeedProvider.TWELVE_DATA, twelve_data_api_key="test-key")
    provider = create_provider(settings)
    assert isinstance(provider, TwelveDataProvider)


def test_twelve_data_without_an_api_key_raises() -> None:
    # Explicit empty string, not just omitted — Settings also reads
    # backend/.env, which may have a real key configured for manual runs.
    settings = Settings(feed_provider=FeedProvider.TWELVE_DATA, twelve_data_api_key="")
    with pytest.raises(ValueError, match="twelve_data_api_key"):
        create_provider(settings)
