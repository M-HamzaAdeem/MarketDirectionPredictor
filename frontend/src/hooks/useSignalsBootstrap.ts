import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { ApiError } from '../services/apiClient'
import { getSignalLatest } from '../services/api'
import { useMarketStore } from '../store/marketStore'
import { ALL_DATA_SOURCES, ALL_SYMBOLS } from '../types/market'
import type { DataSource } from '../types/market'
import type { Signal } from '../types/signal'

const PAIRS = ALL_DATA_SOURCES.flatMap((source) => ALL_SYMBOLS.map((symbol) => ({ source, symbol })))

async function fetchAllLatestSignals(): Promise<{ source: DataSource; signal: Signal }[]> {
  const settled = await Promise.allSettled(PAIRS.map(({ symbol, source }) => getSignalLatest(symbol, source)))
  return settled.flatMap((result, index) => {
    if (result.status === 'fulfilled') return [{ source: PAIRS[index].source, signal: result.value }]

    // No open signal and no winning-caliber setup right now — expected,
    // skip it rather than letting one pair's 404 fail the whole
    // bootstrap. Anything else (500, network failure) is a real problem
    // worth surfacing rather than silently dropping.
    const isNotFound = result.reason instanceof ApiError && result.reason.status === 404
    if (!isNotFound) {
      const { source, symbol } = PAIRS[index]
      console.warn(`[useSignalsBootstrap] ${source}/${symbol} failed`, result.reason)
    }
    return []
  })
}

/** Fetches the latest signal for every symbol, for every source, once on
 * mount and seeds the store — the already-open signal if one exists, or
 * one computed on demand from whatever closed candles already exist, so
 * Open Signals doesn't sit empty after a restart until the next live 15m
 * close. Both sources are fetched regardless of which is currently
 * active, so toggling never needs a refetch. useMarketSocket keeps it
 * live afterward. */
export function useSignalsBootstrap(): void {
  const hydrateSignals = useMarketStore((state) => state.hydrateSignals)
  const { data } = useQuery({ queryKey: ['signals', 'latest', 'all'], queryFn: fetchAllLatestSignals })

  useEffect(() => {
    if (data) {
      const bySource = new Map<DataSource, Signal[]>()
      for (const { source, signal } of data) {
        const forSource = bySource.get(source) ?? []
        forSource.push(signal)
        bySource.set(source, forSource)
      }
      for (const [source, signals] of bySource) {
        hydrateSignals(source, signals)
      }
    }
  }, [data, hydrateSignals])
}
