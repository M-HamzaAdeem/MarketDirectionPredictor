import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { ApiError } from '../services/apiClient'
import { getPredictionLatest } from '../services/api'
import { useMarketStore } from '../store/marketStore'
import { ALL_DATA_SOURCES, ALL_SYMBOLS, ALL_TIMEFRAMES } from '../types/market'
import type { DataSource } from '../types/market'
import type { Prediction } from '../types/prediction'

const PAIRS = ALL_DATA_SOURCES.flatMap((source) =>
  ALL_SYMBOLS.flatMap((symbol) => ALL_TIMEFRAMES.map((timeframe) => ({ source, symbol, timeframe }))),
)

async function fetchAllLatestPredictions(): Promise<{ source: DataSource; prediction: Prediction }[]> {
  const settled = await Promise.allSettled(
    PAIRS.map(({ symbol, timeframe, source }) => getPredictionLatest(symbol, timeframe, source)),
  )
  return settled.flatMap((result, index) => {
    if (result.status === 'fulfilled') return [{ source: PAIRS[index].source, prediction: result.value }]

    // A symbol/timeframe with no closed candles yet 404s — expected, skip
    // it rather than letting one missing pair fail the whole bootstrap.
    // Anything else (500, network failure) is a real problem worth
    // surfacing rather than silently dropping.
    const isNotFound = result.reason instanceof ApiError && result.reason.status === 404
    if (!isNotFound) {
      const { source, symbol, timeframe } = PAIRS[index]
      console.warn(`[usePredictionsBootstrap] ${source}/${symbol}/${timeframe} failed`, result.reason)
    }
    return []
  })
}

/** Fetches an on-demand prediction for every symbol x timeframe x source
 * once on mount and seeds the store, so the dashboard shows real data
 * immediately — even for slower timeframes that haven't had a live candle
 * close yet — instead of waiting for the first WebSocket push. Both
 * sources are fetched regardless of which is currently active, so
 * toggling never needs a refetch. useMarketSocket keeps it live afterward. */
export function usePredictionsBootstrap(): void {
  const setPrediction = useMarketStore((state) => state.setPrediction)
  const { data } = useQuery({ queryKey: ['predictions', 'latest', 'all'], queryFn: fetchAllLatestPredictions })

  useEffect(() => {
    if (data) {
      for (const { source, prediction } of data) {
        setPrediction(source, prediction)
      }
    }
  }, [data, setPrediction])
}
