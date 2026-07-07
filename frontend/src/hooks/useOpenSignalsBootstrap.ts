import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { getOpenSignals } from '../services/api'
import { useMarketStore } from '../store/marketStore'

/** Fetches the currently-open signals once on mount and seeds the store;
 * useMarketSocket keeps it live (new signals + resolutions) afterward. */
export function useOpenSignalsBootstrap(): void {
  const hydrateSignals = useMarketStore((state) => state.hydrateSignals)
  const { data } = useQuery({ queryKey: ['signals', 'open'], queryFn: () => getOpenSignals() })

  useEffect(() => {
    if (data) {
      hydrateSignals(data)
    }
  }, [data, hydrateSignals])
}
