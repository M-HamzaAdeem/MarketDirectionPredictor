import { useQuery } from '@tanstack/react-query'
import { getPredictionHistory } from '../services/api'
import type { MarketSymbol, Timeframe } from '../types/market'

export function usePredictionHistory(symbol: MarketSymbol, timeframe: Timeframe, limit = 100) {
  return useQuery({
    queryKey: ['predictions', 'history', symbol, timeframe, limit],
    queryFn: () => getPredictionHistory(symbol, timeframe, limit),
  })
}
