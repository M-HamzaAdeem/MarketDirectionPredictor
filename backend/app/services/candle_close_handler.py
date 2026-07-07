"""Protocol for anything that reacts to a newly-closed candle. FeedService
holds a list of these rather than a named constructor parameter per
reaction, so adding a new reaction (this project already has three:
PredictionService, SignalTracker, SignalService) never requires touching
FeedService's constructor again.

Handlers run sequentially, in list order, and that order can be load-
bearing (see the comment on `candle_close_handlers` in main.py's
_lifespan) — this Protocol doesn't express or enforce ordering itself."""

from typing import Protocol

from app.feeds.base import Candle


class CandleCloseHandler(Protocol):
    async def on_candle_closed(self, candle: Candle) -> None: ...
