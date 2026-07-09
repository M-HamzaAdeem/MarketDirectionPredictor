import type { Timeframe } from '../types/market'

// Mirrors the backend's app/utils/time.py _TIMEFRAME_SECONDS -- kept in
// sync manually since there's no shared schema between the two stacks.
const TIMEFRAME_SECONDS: Record<Timeframe, number> = {
  '1m': 60,
  '5m': 300,
  '15m': 900,
  '1h': 3600,
  '4h': 14400,
  '1d': 86400,
  '1w': 604800,
}

export interface FormingCandleState {
  open_time: string
  open: number
  high: number
  low: number
  close: number
}

/** Floors an ISO timestamp to the start of its timeframe bucket, in UTC —
 * the client-side equivalent of the backend's bucket_start(), needed
 * because neither pipeline ever persists the still-forming candle (see
 * TradingViewFeedService._split_forming / CandleAggregator), so the chart
 * has to track it itself from live price ticks to show a live bar at all. */
export function bucketStart(timestamp: string, timeframe: Timeframe): string {
  const seconds = TIMEFRAME_SECONDS[timeframe]
  const epochSeconds = Math.floor(new Date(timestamp).getTime() / 1000)
  const flooredSeconds = Math.floor(epochSeconds / seconds) * seconds
  return new Date(flooredSeconds * 1000).toISOString()
}

/** Folds one new price tick into the running forming-candle state. Same
 * bucket as `previous` -> extend high/low, update close, keep open. A
 * later bucket (or no previous state at all) -> start fresh, since a
 * single tick can't tell us the true open of a bucket it didn't observe
 * the start of -- this tick's price is the best available approximation. */
export function updateFormingCandle(
  previous: FormingCandleState | null,
  price: number,
  timestamp: string,
  timeframe: Timeframe,
): FormingCandleState {
  const openTime = bucketStart(timestamp, timeframe)

  if (previous !== null && previous.open_time === openTime) {
    return { ...previous, high: Math.max(previous.high, price), low: Math.min(previous.low, price), close: price }
  }

  return { open_time: openTime, open: price, high: price, low: price, close: price }
}

/** Whether the forming candle's bucket has already been confirmed closed
 * by the backend (i.e. `lastClosedOpenTime`, from the REST-fetched candle
 * list, is at or past it) — if so, PriceChart must defer to that rather
 * than re-drawing this hook's now-stale approximation of the same bar.
 *
 * Compares epoch instants, not the raw ISO strings, deliberately: this
 * repo's confirmed backend format (whole-second candle timestamps
 * serialize as `...T10:15:00Z`, no fractional seconds) happens to agree
 * with `bucketStart()`'s `.000Z`-suffixed output under plain string
 * comparison today, but only because of that specific formatting
 * asymmetry — nothing guarantees it stays true if either side's
 * serialization ever changes (e.g. a `+00:00` offset instead of `Z`
 * would flip the comparison). Comparing epoch instants makes the
 * behavior correct independent of either side's exact string format. */
export function formingCandleIsStale(formingOpenTime: string, lastClosedOpenTime: string | null): boolean {
  if (lastClosedOpenTime === null) return false
  return new Date(formingOpenTime).getTime() <= new Date(lastClosedOpenTime).getTime()
}
