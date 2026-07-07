import { useQuery } from '@tanstack/react-query'
import { getCandles } from '../services/api'
import type { MarketSymbol, Timeframe } from '../types/market'

export function useCandles(symbol: MarketSymbol, timeframe: Timeframe, limit = 200) {
  return useQuery({
    queryKey: ['candles', symbol, timeframe, limit],
    queryFn: () => getCandles(symbol, timeframe, limit),
  })
}
