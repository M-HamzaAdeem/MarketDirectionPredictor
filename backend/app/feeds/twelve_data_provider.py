"""MarketDataProvider backed by Twelve Data's REST + WebSocket API.

`fetch_history()` calls the `time_series` REST endpoint for historical
backfill; `stream_ticks()` opens Twelve Data's real-time price WebSocket.
Reconnection on a dropped stream is handled entirely by FeedService's
existing backoff loop (Phase 8) — this provider only needs to raise (or let
its generator end) on failure; it must not retry internally, or the two
reconnect loops would compound.

Verified empirically against a free "Basic" plan account: `time_series`
covers XAU/USD, EUR/USD, and AUD/USD at 1min/5min/15min/1h/4h; the
WebSocket delivers live price pushes for all three within seconds of
subscribing. Neither surface reports real volume — forex/commodities are
OTC, there's no exchange tape to report a trade volume from — every Tick
and Candle this provider produces carries volume=0.0.

The `time_series` endpoint's `datetime` field is NOT UTC by default (it's
"Exchange" local time, confirmed empirically — the same candle came back
with a ~10 hour offset depending on the `timezone` param), so every
request explicitly passes `timezone=UTC`. Never drop that parameter.

The API key goes in an `Authorization: apikey <key>` header for REST calls
(confirmed working), never a query parameter — httpx logs full request
URLs at INFO level, and a query-param key would leak into those logs (hit
this for real running the backtest CLI; see decisions.md). The WebSocket
unfortunately has no header-auth equivalent — Twelve Data's server
rejects the handshake without `?apikey=` in the URL (confirmed) — so that
one URL is the one place the key still appears in a string; nothing in
this codebase logs it.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx
from websockets import connect as _default_ws_connect

from app.core.constants import FeedStatus, Symbol, Timeframe
from app.feeds.base import Candle, MarketDataProvider, Tick
from app.utils.time import timeframe_seconds

logger = logging.getLogger(__name__)

_REST_BASE_URL = "https://api.twelvedata.com"
_WS_URL = "wss://ws.twelvedata.com/v1/quotes/price"
_REQUEST_TIMEOUT_SECONDS = 10.0
# Free-tier rate limit is 8 requests/minute; spacing fetch_history calls
# this far apart keeps a full 3-symbol x 5-timeframe backfill comfortably
# under it instead of racing 15 requests out immediately and getting
# rate-limited partway through.
_MIN_REQUEST_INTERVAL_SECONDS = 8.0

_SYMBOL_TO_INSTRUMENT: dict[Symbol, str] = {
    Symbol.XAUUSD: "XAU/USD",
    Symbol.EURUSD: "EUR/USD",
    Symbol.AUDUSD: "AUD/USD",
}
_INSTRUMENT_TO_SYMBOL = {v: k for k, v in _SYMBOL_TO_INSTRUMENT.items()}

_TIMEFRAME_TO_INTERVAL: dict[Timeframe, str] = {
    Timeframe.M1: "1min",
    Timeframe.M5: "5min",
    Timeframe.M15: "15min",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
}


class _WebSocketConnection(Protocol):
    async def send(self, message: str) -> None: ...
    def __aiter__(self) -> AsyncIterator[str]: ...


class TwelveDataProvider(MarketDataProvider):
    """`ws_connect` is injectable (defaults to the real `websockets.connect`)
    so tests can substitute a fake connection instead of hitting the network
    — same pattern as `http_client`."""

    def __init__(
        self,
        api_key: str,
        http_client: httpx.AsyncClient | None = None,
        ws_connect: Callable[[str], AbstractAsyncContextManager[_WebSocketConnection]] = _default_ws_connect,
        min_request_interval_seconds: float = _MIN_REQUEST_INTERVAL_SECONDS,
    ) -> None:
        if not api_key:
            raise ValueError("TwelveDataProvider requires a non-empty api_key")

        self._api_key = api_key
        self._http = http_client or httpx.AsyncClient(base_url=_REST_BASE_URL, timeout=_REQUEST_TIMEOUT_SECONDS)
        self._owns_http_client = http_client is None
        self._ws_connect = ws_connect
        self._min_request_interval_seconds = min_request_interval_seconds
        self._last_request_at: float | None = None
        self._connected = False

    @property
    def nominal_status(self) -> FeedStatus:
        return FeedStatus.LIVE

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False
        if self._owns_http_client:
            await self._http.aclose()

    async def fetch_history(self, symbol: Symbol, timeframe: Timeframe, count: int) -> list[Candle]:
        await self._throttle()

        response = await self._http.get(
            "/time_series",
            params={
                "symbol": _SYMBOL_TO_INSTRUMENT[symbol],
                "interval": _TIMEFRAME_TO_INTERVAL[timeframe],
                "outputsize": count,
                "timezone": "UTC",
            },
            headers={"Authorization": f"apikey {self._api_key}"},
        )
        response.raise_for_status()
        payload = response.json()

        if payload.get("status") == "error":
            raise RuntimeError(
                f"Twelve Data error fetching {symbol.value}/{timeframe.value}: {payload.get('message')}"
            )

        # API returns newest-first; storage/consumers expect ascending order.
        rows = list(reversed(payload.get("values", [])))
        return [_row_to_candle(symbol, timeframe, row) for row in rows]

    async def stream_ticks(self, symbols: list[Symbol]) -> AsyncIterator[Tick]:
        if not self._connected:
            raise RuntimeError("TwelveDataProvider.connect() must be called before streaming")

        instruments = ",".join(_SYMBOL_TO_INSTRUMENT[symbol] for symbol in symbols)
        async with self._ws_connect(f"{_WS_URL}?apikey={self._api_key}") as ws:
            await ws.send(json.dumps({"action": "subscribe", "params": {"symbols": instruments}}))
            async for raw in ws:
                tick = _parse_price_event(raw)
                if tick is not None:
                    yield tick

    async def _throttle(self) -> None:
        # Not concurrency-safe (no lock around the check-then-set below) —
        # only correct because FeedService.backfill() awaits each
        # fetch_history call in sequence, never concurrently. A future
        # concurrent caller would need a lock here.
        loop = asyncio.get_running_loop()
        if self._last_request_at is not None:
            remaining = self._min_request_interval_seconds - (loop.time() - self._last_request_at)
            if remaining > 0:
                await asyncio.sleep(remaining)
        self._last_request_at = loop.time()


def _row_to_candle(symbol: Symbol, timeframe: Timeframe, row: dict[str, Any]) -> Candle:
    open_time = datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    return Candle(
        symbol=symbol,
        timeframe=timeframe,
        open_time=open_time,
        close_time=open_time + timedelta(seconds=timeframe_seconds(timeframe)),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        # Forex/commodities are OTC — Twelve Data never reports volume for
        # them. Hard-coded, not `row.get("volume", 0.0)`: the volume-profile
        # zero-volume guard (see decisions.md) depends on this being exactly
        # 0.0, not whatever a future response happens to include.
        volume=0.0,
    )


def _parse_price_event(raw: str) -> Tick | None:
    try:
        message = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Dropping malformed Twelve Data WebSocket frame")
        return None

    if message.get("event") != "price":
        return None

    symbol = _INSTRUMENT_TO_SYMBOL.get(message.get("symbol"))
    if symbol is None:
        return None

    try:
        return Tick(
            symbol=symbol,
            price=float(message["price"]),
            timestamp=datetime.fromtimestamp(message["timestamp"], tz=UTC),
            volume=0.0,
        )
    except (KeyError, TypeError, ValueError):
        logger.warning("Dropping malformed Twelve Data price event")
        return None
