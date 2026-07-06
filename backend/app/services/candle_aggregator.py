"""Rolls ticks into OHLC candles per configured timeframe.

Pure and synchronous by design — no I/O — so the aggregation rules are
unit-testable without a database or event loop. Persistence and broadcast
of the candles this emits are the caller's responsibility (see
services/feed_service.py).
"""

from datetime import timedelta

from app.core.constants import Symbol, Timeframe
from app.feeds.base import Candle, Tick
from app.utils.time import bucket_start, timeframe_seconds


class _OpenCandle:
    __slots__ = ("open_time", "open", "high", "low", "close", "volume")

    def __init__(self, open_time, price: float, volume: float = 0.0) -> None:
        self.open_time = open_time
        self.open = price
        self.high = price
        self.low = price
        self.close = price
        self.volume = volume

    def update(self, price: float, volume: float) -> None:
        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += volume


class CandleAggregator:
    """Maintains one in-progress candle per (symbol, timeframe) and emits a
    closed Candle whenever a tick lands in the next bucket."""

    def __init__(self, timeframes: list[Timeframe]) -> None:
        self._timeframes = timeframes
        self._open: dict[tuple[Symbol, Timeframe], _OpenCandle] = {}

    def ingest(self, tick: Tick) -> list[Candle]:
        closed: list[Candle] = []
        for timeframe in self._timeframes:
            key = (tick.symbol, timeframe)
            bucket = bucket_start(tick.timestamp, timeframe)
            current = self._open.get(key)

            if current is None:
                self._open[key] = _OpenCandle(bucket, tick.price, tick.volume)
            elif bucket != current.open_time:
                closed.append(self._finalize(tick.symbol, timeframe, current))
                self._open[key] = _OpenCandle(bucket, tick.price, tick.volume)
            else:
                current.update(tick.price, tick.volume)

        return closed

    def _finalize(self, symbol: Symbol, timeframe: Timeframe, candle: _OpenCandle) -> Candle:
        close_time = candle.open_time + timedelta(seconds=timeframe_seconds(timeframe))
        return Candle(
            symbol=symbol,
            timeframe=timeframe,
            open_time=candle.open_time,
            close_time=close_time,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )
