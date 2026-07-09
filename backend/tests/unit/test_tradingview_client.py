import asyncio
import json

import pytest

from app.core.constants import Symbol, Timeframe
from app.feeds.tradingview_client import TradingViewClient


def _tv_frame(payload: dict) -> str:
    text = json.dumps(payload, separators=(",", ":"))
    return f"~m~{len(text)}~m~{text}"


def _du_frame(index: int, values: list[float]) -> str:
    return _tv_frame({"m": "du", "p": ["cs_x", {"sds_1": {"s": [{"i": index, "v": values}]}}]})


_SERIES_COMPLETED_FRAME = _tv_frame({"m": "series_completed", "p": ["cs_x", "sds_1", "s1"]})


class _FakeWebSocketConnection:
    def __init__(self, frames: list[str], hang_after: bool = False) -> None:
        self.sent: list[str] = []
        self._frames = frames
        self._hang_after = hang_after

    async def send(self, message: str) -> None:
        self.sent.append(message)

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for frame in self._frames:
            yield frame
        if self._hang_after:
            await asyncio.Event().wait()  # never resolves -- simulates a hung read


class _FakeWsConnect:
    def __init__(self, connection: _FakeWebSocketConnection) -> None:
        self._connection = connection
        self.url: str | None = None

    def __call__(self, url: str):
        self.url = url
        return self

    async def __aenter__(self):
        return self._connection

    async def __aexit__(self, *exc_info):
        return False


async def test_fetch_candles_parses_bars_ascending_by_open_time() -> None:
    frames = [
        _du_frame(0, [1735689660.0, 100.9, 102.0, 100.5, 101.5, 50.0]),  # sent second, but the earlier open_time
        _du_frame(1, [1735689600.0, 100.1, 101.2, 99.8, 100.9, 123.0]),  # deliberately out of order in transit
        _SERIES_COMPLETED_FRAME,
    ]
    ws_connect = _FakeWsConnect(_FakeWebSocketConnection(frames))
    client = TradingViewClient(exchange="OANDA", ws_connect=ws_connect)

    candles = await client.fetch_candles(Symbol.XAUUSD, Timeframe.M1, count=100)

    assert len(candles) == 2
    assert candles[0].open_time < candles[1].open_time
    assert candles[0].close == 100.9
    assert candles[1].close == 101.5
    assert candles[0].symbol == Symbol.XAUUSD
    assert candles[0].timeframe == Timeframe.M1


async def test_fetch_candles_sends_the_expected_handshake_in_order() -> None:
    ws_connect = _FakeWsConnect(_FakeWebSocketConnection([_SERIES_COMPLETED_FRAME]))
    client = TradingViewClient(exchange="OANDA", ws_connect=ws_connect)

    await client.fetch_candles(Symbol.XAUUSD, Timeframe.M15, count=100)

    sent_methods = [json.loads(frame.split("~m~")[2])["m"] for frame in ws_connect._connection.sent]
    assert sent_methods == [
        "set_auth_token",
        "chart_create_session",
        "quote_create_session",
        "resolve_symbol",
        "create_series",
        "switch_timezone",
    ]
    resolve_symbol_params = json.loads(ws_connect._connection.sent[3].split("~m~")[2])["p"]
    assert resolve_symbol_params[2].startswith("=")
    assert "OANDA:XAUUSD" in resolve_symbol_params[2]
    create_series_params = json.loads(ws_connect._connection.sent[4].split("~m~")[2])["p"]
    assert create_series_params[4] == "15"  # Timeframe.M15 -> TradingView's "15" interval string


async def test_fetch_candles_drops_a_malformed_bar_without_raising() -> None:
    frames = [
        _tv_frame({"m": "du", "p": ["cs_x", {"sds_1": {"s": [{"i": 0, "v": [1735689600.0, "not-a-number", 101, 99, 100]}]}}]}),
        _du_frame(1, [1735689660.0, 100.9, 102.0, 100.5, 101.5, 0.0]),
        _SERIES_COMPLETED_FRAME,
    ]
    ws_connect = _FakeWsConnect(_FakeWebSocketConnection(frames))
    client = TradingViewClient(ws_connect=ws_connect)

    candles = await client.fetch_candles(Symbol.XAUUSD, Timeframe.M1, count=100)

    assert len(candles) == 1
    assert candles[0].close == 101.5


async def test_fetch_candles_times_out_if_series_completed_never_arrives() -> None:
    connection = _FakeWebSocketConnection([_du_frame(0, [1735689600.0, 100.0, 101.0, 99.0, 100.5, 0.0])], hang_after=True)
    ws_connect = _FakeWsConnect(connection)
    client = TradingViewClient(ws_connect=ws_connect, request_timeout_seconds=0.05)

    with pytest.raises(TimeoutError, match="series_completed"):
        await client.fetch_candles(Symbol.XAUUSD, Timeframe.M1, count=100)
