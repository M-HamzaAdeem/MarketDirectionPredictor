"""Generates new ICT signals whenever a fresh 15m candle closes: fetches
the 4H/1H/15m candle windows for the candle's symbol, runs them through
build_signal(), and persists + broadcasts anything produced.

Only ever acts on 15m candle closes — that's the signal builder's entry
confirmation timeframe (see prediction/signal_builder.py); a 4H or 1H
close doesn't need to re-trigger this, since bias/setup only matter once
an actual entry tap is confirmed on 15m.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.constants import Timeframe
from app.feeds.base import Candle
from app.prediction.signal_builder import build_signal
from app.services.broadcast_service import BroadcastService
from app.storage.repositories.candle_repository import CandleRepository
from app.storage.repositories.signal_repository import SignalRepository

# Public, not underscore-prefixed: app/backtesting/signal_backtest.py is a
# second real reader, replaying build_signal() with these exact windows so
# backtested behavior can't silently diverge from live.
CANDLE_WINDOW_4H = 60
CANDLE_WINDOW_1H = 100
CANDLE_WINDOW_15M = 20


class SignalService:
    def __init__(self, broadcaster: BroadcastService, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._broadcaster = broadcaster
        self._session_factory = session_factory

    async def on_candle_closed(self, candle: Candle) -> None:
        if candle.timeframe != Timeframe.M15:
            return

        async with self._session_factory() as session:
            candle_repository = CandleRepository(session)
            candles_4h = await candle_repository.get_recent(candle.symbol, Timeframe.H4, limit=CANDLE_WINDOW_4H)
            candles_1h = await candle_repository.get_recent(candle.symbol, Timeframe.H1, limit=CANDLE_WINDOW_1H)
            candles_15m = await candle_repository.get_recent(
                candle.symbol, Timeframe.M15, limit=CANDLE_WINDOW_15M
            )

            signal = build_signal(candle.symbol, candles_4h, candles_1h, candles_15m)
            if signal is None:
                return

            saved = await SignalRepository(session).save(signal)

        await self._broadcaster.broadcast_signal(saved)
