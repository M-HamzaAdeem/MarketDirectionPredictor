import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { ApiError } from '../services/apiClient'
import { getSignalLatest } from '../services/api'
import { useMarketStore } from '../store/marketStore'
import { ALL_SYMBOLS } from '../types/market'
import type { Signal } from '../types/signal'

async function fetchAllLatestSignals(): Promise<Signal[]> {
  const settled = await Promise.allSettled(ALL_SYMBOLS.map((symbol) => getSignalLatest(symbol)))
  return settled.flatMap((result, index) => {
    if (result.status === 'fulfilled') return [result.value]

    // No open signal and no winning-caliber setup right now — expected,
    // skip it rather than letting one symbol's 404 fail the whole
    // bootstrap. Anything else (500, network failure) is a real problem
    // worth surfacing rather than silently dropping.
    const isNotFound = result.reason instanceof ApiError && result.reason.status === 404
    if (!isNotFound) {
      console.warn(`[useSignalsBootstrap] ${ALL_SYMBOLS[index]} failed`, result.reason)
    }
    return []
  })
}

/** Fetches the latest signal for every symbol once on mount and seeds the
 * store — the already-open signal if one exists, or one computed on
 * demand from whatever closed candles already exist, so Open Signals
 * doesn't sit empty after a restart until the next live 15m close.
 * useMarketSocket keeps it live afterward. */
export function useSignalsBootstrap(): void {
  const hydrateSignals = useMarketStore((state) => state.hydrateSignals)
  const { data } = useQuery({ queryKey: ['signals', 'latest', 'all'], queryFn: fetchAllLatestSignals })

  useEffect(() => {
    if (data) {
      hydrateSignals(data)
    }
  }, [data, hydrateSignals])
}
