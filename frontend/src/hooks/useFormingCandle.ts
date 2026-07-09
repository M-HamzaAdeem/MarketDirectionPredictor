import { useEffect, useRef, useState } from 'react'
import { useActivePrices } from '../store/marketStore'
import type { Candle, MarketSymbol, Timeframe } from '../types/market'
import { type FormingCandleState, updateFormingCandle } from '../utils/formingCandle'

/** Tracks a live, still-forming candle for `symbol`/`timeframe` from price
 * ticks in the active source's live-price cache -- neither pipeline ever
 * persists the currently-forming bar (see TradingViewFeedService /
 * CandleAggregator), so without this the chart only ever shows the last
 * *closed* bar, one bar behind what a live chart (e.g. TradingView's own)
 * shows. Returns `null` until the first price tick arrives for this pair. */
export function useFormingCandle(symbol: MarketSymbol, timeframe: Timeframe): Candle | null {
  const price = useActivePrices()[symbol]
  const [forming, setForming] = useState<FormingCandleState | null>(null)
  // Two writers can touch this symbol's price entry -- the live WebSocket
  // tick and usePricesBootstrap's fallback seed -- so a stale/duplicate
  // timestamp landing after a newer one already applied must not fold in
  // and overwrite the current close (or re-widen high/low) with older data.
  const lastAppliedTimestampMs = useRef<number | null>(null)

  // A new symbol/timeframe selection has no relationship to whatever bar
  // was forming for the previous one -- start clean rather than carrying
  // stale OHLC state across the switch.
  useEffect(() => {
    setForming(null)
    lastAppliedTimestampMs.current = null
  }, [symbol, timeframe])

  useEffect(() => {
    if (!price) return
    const tickMs = new Date(price.timestamp).getTime()
    if (lastAppliedTimestampMs.current !== null && tickMs <= lastAppliedTimestampMs.current) return
    lastAppliedTimestampMs.current = tickMs
    setForming((previous) => updateFormingCandle(previous, price.price, price.timestamp, timeframe))
  }, [price, timeframe])

  if (forming === null) return null
  return {
    open_time: forming.open_time,
    // Placeholder: the forming bar has no real close yet ("now," not a
    // fixed instant) -- unused today since PriceChart only reads open_time.
    close_time: forming.open_time,
    open: forming.open,
    high: forming.high,
    low: forming.low,
    close: forming.close,
    volume: 0,
  }
}
