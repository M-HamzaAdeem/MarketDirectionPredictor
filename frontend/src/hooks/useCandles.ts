import { useQuery } from '@tanstack/react-query'
import { getCandles } from '../services/api'
import type { DataSource, MarketSymbol, Timeframe } from '../types/market'

// Exported so useMarketSocket can invalidate exactly this key (by
// symbol/timeframe/source prefix) when a live prediction message signals
// this pair's candle list is stale — a literal-string copy there would
// silently drift out of sync with this key shape and no test would catch
// it. `source` is part of the key itself (not just a query param on the
// request) so a TradingView candle-close can never invalidate/refetch the
// Twelve Data cache entry for the same symbol/timeframe, or vice versa.
export function candlesKey(
  symbol: MarketSymbol,
  timeframe: Timeframe,
  source: DataSource,
): readonly [string, MarketSymbol, Timeframe, DataSource] {
  return ['candles', symbol, timeframe, source] as const
}

export function useCandles(symbol: MarketSymbol, timeframe: Timeframe, source: DataSource, limit = 200) {
  return useQuery({
    queryKey: [...candlesKey(symbol, timeframe, source), limit],
    queryFn: () => getCandles(symbol, timeframe, source, limit),
  })
}
