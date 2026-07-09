import { useQuery } from '@tanstack/react-query'
import { getSignalHistory } from '../services/api'
import type { DataSource, MarketSymbol } from '../types/market'

// Exported so useMarketSocket can invalidate exactly this key (by
// symbol/source prefix) when a live signal message signals this symbol's
// history is stale — a literal-string copy there would silently drift out
// of sync with this key shape and no test would catch it. `source` is
// part of the key itself so a TradingView signal can never
// invalidate/refetch the Twelve Data history cache entry, or vice versa.
export function signalHistoryKey(
  symbol: MarketSymbol,
  source: DataSource,
): readonly [string, string, MarketSymbol, DataSource] {
  return ['signals', 'history', symbol, source] as const
}

export function useSignalHistory(symbol: MarketSymbol, source: DataSource, limit = 100) {
  return useQuery({
    queryKey: [...signalHistoryKey(symbol, source), limit],
    queryFn: () => getSignalHistory(symbol, source, limit),
  })
}
