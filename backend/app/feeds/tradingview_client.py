"""TradingView's unofficial WebSocket protocol — there is no official
public market-data API for fetching chart candles from TradingView; this
implements the internal/raw protocol a browser tab uses, which can break
if TradingView changes it. R&D-grade, not a production data guarantee —
see Settings.tradingview_enabled (defaults off) in core/config.py.

Not a MarketDataProvider: TradingView's protocol is poll-based (connect,
request, receive, disconnect per fetch), not a persistent tick stream, and
it hands back pre-aggregated OHLC bars rather than individual price ticks
— aggregating ticks into candles (CandleAggregator) doesn't apply here.
app/services/tradingview_feed_service.py is this client's poll-loop
orchestrator.

`fetch_candles` must raise (never retry internally) on failure — same
contract as TwelveDataProvider — so TradingViewFeedService's own backoff
loop is the only place retries happen.
"""

import asyncio
import json
import logging
import random
import re
import string
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from typing import Protocol

from websockets import connect as _default_ws_connect

from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle
from app.utils.time import timeframe_seconds

logger = logging.getLogger(__name__)

_WS_URL = "wss://data.tradingview.com/socket.io/websocket"
_ORIGIN = "https://data.tradingview.com"
_AUTH_TOKEN = "unauthorized_user_token"
_SERIES_COMPLETED_MARKER = "series_completed"
_DEFAULT_REQUEST_TIMEOUT_SECONDS = 15.0

_TIMEFRAME_TO_INTERVAL: dict[Timeframe, str] = {
    Timeframe.M1: "1",
    Timeframe.M5: "5",
    Timeframe.M15: "15",
    Timeframe.H1: "60",
    Timeframe.H4: "240",
}

# TradingView's replies embed candle rows as e.g. "v":[1735689600,100.1,...]
# directly in the raw frame text — extracting via regex over the whole
# accumulated buffer works without needing to parse the surrounding
# ~m~len~m~{...} envelope into structured JSON at all.
_CANDLE_VALUES_PATTERN = re.compile(r'"v":\[([^\]]+)\]')


class _WebSocketConnection(Protocol):
    async def send(self, message: str) -> None: ...
    def __aiter__(self) -> AsyncIterator[str]: ...


def _default_tradingview_ws_connect(url: str) -> AbstractAsyncContextManager[_WebSocketConnection]:
    # TradingView's server requires this Origin or rejects the handshake.
    return _default_ws_connect(url, origin=_ORIGIN)


def _random_session_id(prefix: str, length: int = 12) -> str:
    return prefix + "".join(random.choice(string.ascii_lowercase) for _ in range(length))


def _frame(method: str, params: list[object]) -> str:
    payload = json.dumps({"m": method, "p": params}, separators=(",", ":"))
    return f"~m~{len(payload)}~m~{payload}"


class TradingViewClient:
    """`fetch_candles` does one full connect -> handshake -> receive ->
    close cycle per call. `ws_connect` is injectable (defaults to a real
    `websockets.connect` with the Origin header TradingView requires) so
    tests can substitute a fake connection instead of hitting the network
    — same pattern as TwelveDataProvider's `ws_connect`."""

    def __init__(
        self,
        exchange: str = "OANDA",
        ws_connect: Callable[
            [str], AbstractAsyncContextManager[_WebSocketConnection]
        ] = _default_tradingview_ws_connect,
        request_timeout_seconds: float = _DEFAULT_REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self._exchange = exchange
        self._ws_connect = ws_connect
        self._request_timeout_seconds = request_timeout_seconds

    async def fetch_candles(self, symbol: Symbol, timeframe: Timeframe, count: int) -> list[Candle]:
        """Returns ALL bars TradingView sends back, ascending by open_time,
        INCLUDING the last one — which is always still-forming/provisional,
        per TradingView's own documented behavior. The caller decides which
        bars are safe to treat as closed; this method never assumes it."""
        chart_session = _random_session_id("cs_")
        quote_session = _random_session_id("qs_")
        formatted_symbol = f"{self._exchange}:{symbol.value}"
        interval = _TIMEFRAME_TO_INTERVAL[timeframe]

        async with self._ws_connect(_WS_URL) as ws:
            await ws.send(_frame("set_auth_token", [_AUTH_TOKEN]))
            await ws.send(_frame("chart_create_session", [chart_session, ""]))
            await ws.send(_frame("quote_create_session", [quote_session]))

            symbol_payload = json.dumps({"symbol": formatted_symbol, "adjustment": "splits", "session": "regular"})
            await ws.send(_frame("resolve_symbol", [chart_session, "symbol_1", f"={symbol_payload}"]))
            await ws.send(_frame("create_series", [chart_session, "sds_1", "s1", "symbol_1", interval, count]))
            await ws.send(_frame("switch_timezone", [chart_session, "exchange"]))

            raw = await self._receive_until_completed(ws)

        return _extract_candles(raw, symbol, timeframe)

    async def _receive_until_completed(self, ws: _WebSocketConnection) -> str:
        # An undocumented, unofficial protocol has no known keepalive/error
        # framing — a hung read (TradingView never sends series_completed)
        # must not block a poll cycle forever.
        async def _read() -> str:
            buffer = ""
            async for message in ws:
                buffer += message
                if _SERIES_COMPLETED_MARKER in message:
                    break
            return buffer

        try:
            return await asyncio.wait_for(_read(), timeout=self._request_timeout_seconds)
        except TimeoutError as exc:
            raise TimeoutError(
                f"TradingView did not send {_SERIES_COMPLETED_MARKER} within {self._request_timeout_seconds}s"
            ) from exc


def _extract_candles(raw: str, symbol: Symbol, timeframe: Timeframe) -> list[Candle]:
    # Keyed by timestamp so a later frame's snapshot of the still-forming
    # bar (TradingView can push more than one update for it before
    # series_completed) overwrites an earlier, staler one for that bar.
    bars_by_timestamp: dict[float, tuple[float, float, float, float, float]] = {}

    for match in _CANDLE_VALUES_PATTERN.finditer(raw):
        parts = match.group(1).split(",")
        try:
            timestamp, open_, high, low, close = (float(parts[i]) for i in range(5))
            volume = float(parts[5]) if len(parts) > 5 else 0.0
        except (ValueError, IndexError):
            logger.warning("Dropping malformed TradingView candle payload")
            continue
        bars_by_timestamp[timestamp] = (open_, high, low, close, volume)

    seconds = timeframe_seconds(timeframe)
    return [
        Candle(
            symbol=symbol,
            timeframe=timeframe,
            open_time=datetime.fromtimestamp(ts, tz=UTC),
            close_time=datetime.fromtimestamp(ts, tz=UTC) + timedelta(seconds=seconds),
            open=values[0],
            high=values[1],
            low=values[2],
            close=values[3],
            volume=values[4],
        )
        for ts, values in sorted(bars_by_timestamp.items())
    ]
