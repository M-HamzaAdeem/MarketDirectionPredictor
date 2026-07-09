import { useQuery } from '@tanstack/react-query'
import { getCandles } from '../services/api'
import type { MarketSymbol, Timeframe } from '../types/market'

// Exported so useMarketSocket can invalidate exactly this key (by symbol/timeframe
// prefix) when a live prediction message signals this pair's candle list is
// stale — a literal-string copy there would silently drift out of sync with
// this key shape and no test would catch it.
export function candlesKey(symbol: MarketSymbol, timeframe: Timeframe): readonly [string, MarketSymbol, Timeframe] {
  return ['candles', symbol, timeframe] as const
}

export function useCandles(symbol: MarketSymbol, timeframe: Timeframe, limit = 200) {
  return useQuery({
    queryKey: [...candlesKey(symbol, timeframe), limit],
    queryFn: () => getCandles(symbol, timeframe, limit),
  })
}
