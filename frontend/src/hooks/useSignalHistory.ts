import { useQuery } from '@tanstack/react-query'
import { getSignalHistory } from '../services/api'
import type { MarketSymbol } from '../types/market'

// Exported so useMarketSocket can invalidate exactly this key (by symbol
// prefix) when a live signal message signals this symbol's history is
// stale — a literal-string copy there would silently drift out of sync with
// this key shape and no test would catch it.
export function signalHistoryKey(symbol: MarketSymbol): readonly [string, string, MarketSymbol] {
  return ['signals', 'history', symbol] as const
}

export function useSignalHistory(symbol: MarketSymbol, limit = 100) {
  return useQuery({
    queryKey: [...signalHistoryKey(symbol), limit],
    queryFn: () => getSignalHistory(symbol, limit),
  })
}
