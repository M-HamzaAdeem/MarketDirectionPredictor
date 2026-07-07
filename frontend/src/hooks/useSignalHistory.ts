import { useQuery } from '@tanstack/react-query'
import { getSignalHistory } from '../services/api'
import type { MarketSymbol } from '../types/market'

export function useSignalHistory(symbol: MarketSymbol, limit = 100) {
  return useQuery({
    queryKey: ['signals', 'history', symbol, limit],
    queryFn: () => getSignalHistory(symbol, limit),
  })
}
