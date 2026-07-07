import json
import time
from datetime import UTC, datetime

import httpx
import pytest

from app.core.constants import FeedStatus, Symbol, Timeframe
from app.feeds.twelve_data_provider import TwelveDataProvider


def _time_series_response(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/time_series"
    params = request.url.params
    assert params["timezone"] == "UTC"
    assert params["apikey"] == "test-key"
    assert params["symbol"] == "XAU/USD"
    assert params["interval"] == "15min"

    return httpx.Response(
        200,
        json={
            "meta": {"symbol": "XAU/USD", "interval": "15min"},
            "status": "ok",
            # Newest-first, as the real API returns it.
            "values": [
                {"datetime": "2026-01-01 00:30:00", "open": "3", "high": "3.5", "low": "2.9", "close": "3.4"},
                {"datetime": "2026-01-01 00:15:00", "open": "2", "high": "2.5", "low": "1.9", "close": "2.4"},
                {"datetime": "2026-01-01 00:00:00", "open": "1", "high": "1.5", "low": "0.9", "close": "1.4"},
            ],
        },
    )


def _error_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"status": "error", "code": 400, "message": "invalid symbol"})


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.twelvedata.com")


def test_nominal_status_is_live() -> None:
    provider = TwelveDataProvider(api_key="test-key", http_client=_client(_time_series_response))
    assert provider.nominal_status == FeedStatus.LIVE


def test_constructor_rejects_empty_api_key() -> None:
    with pytest.raises(ValueError, match="api_key"):
        TwelveDataProvider(api_key="")


async def test_fetch_history_returns_ascending_order_with_utc_timestamps() -> None:
    provider = TwelveDataProvider(
        api_key="test-key", http_client=_client(_time_series_response), min_request_interval_seconds=0.0
    )

    candles = await provider.fetch_history(Symbol.XAUUSD, Timeframe.M15, count=3)

    assert [c.close for c in candles] == [1.4, 2.4, 3.4]  # oldest first
    first = candles[0]
    assert first.symbol == Symbol.XAUUSD
    assert first.timeframe == Timeframe.M15
    assert first.open_time == datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    assert first.close_time == datetime(2026, 1, 1, 0, 15, tzinfo=UTC)
    assert first.volume == 0.0


async def test_fetch_history_raises_on_api_error_status() -> None:
    provider = TwelveDataProvider(
        api_key="test-key", http_client=_client(_error_response), min_request_interval_seconds=0.0
    )

    with pytest.raises(RuntimeError, match="invalid symbol"):
        await provider.fetch_history(Symbol.XAUUSD, Timeframe.M15, count=3)


async def test_fetch_history_throttles_consecutive_calls() -> None:
    provider = TwelveDataProvider(
        api_key="test-key", http_client=_client(_time_series_response), min_request_interval_seconds=0.1
    )

    start = time.monotonic()
    await provider.fetch_history(Symbol.XAUUSD, Timeframe.M15, count=3)
    await provider.fetch_history(Symbol.XAUUSD, Timeframe.M15, count=3)
    elapsed = time.monotonic() - start

    assert elapsed >= 0.1


async def test_stream_ticks_raises_if_not_connected() -> None:
    provider = TwelveDataProvider(api_key="test-key", http_client=_client(_time_series_response))

    with pytest.raises(RuntimeError, match="connect"):
        async for _ in provider.stream_ticks([Symbol.XAUUSD]):
            pass


class _FakeWebSocketConnection:
    def __init__(self, frames: list[str]) -> None:
        self.sent: list[str] = []
        self._frames = frames

    async def send(self, message: str) -> None:
        self.sent.append(message)

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for frame in self._frames:
            yield frame


class _FakeWsConnect:
    def __init__(self, connection: _FakeWebSocketConnection) -> None:
        self._connection = connection

    def __call__(self, url: str):
        self._url = url
        return self

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, *exc_info):
        return False


async def test_stream_ticks_yields_only_recognized_price_events() -> None:
    frames = [
        json.dumps({"event": "subscribe-status", "status": "ok"}),
        json.dumps({"event": "price", "symbol": "XAU/USD", "price": 4147.6, "timestamp": 1783439040}),
        json.dumps({"event": "price", "symbol": "USD/JPY", "price": 150.0, "timestamp": 1783439040}),
        "not-json",
        json.dumps({"event": "price", "symbol": "XAU/USD"}),  # well-formed JSON, missing price/timestamp
        json.dumps({"event": "price", "symbol": "EUR/USD", "price": 1.1427, "timestamp": 1783439100}),
    ]
    connection = _FakeWebSocketConnection(frames)
    ws_connect = _FakeWsConnect(connection)
    provider = TwelveDataProvider(api_key="test-key", http_client=_client(_time_series_response), ws_connect=ws_connect)
    await provider.connect()

    ticks = [tick async for tick in provider.stream_ticks([Symbol.XAUUSD, Symbol.EURUSD])]

    assert [t.symbol for t in ticks] == [Symbol.XAUUSD, Symbol.EURUSD]
    assert ticks[0].price == 4147.6
    assert ticks[0].volume == 0.0
    subscribe_payload = json.loads(connection.sent[0])
    assert subscribe_payload["params"]["symbols"] == "XAU/USD,EUR/USD"
