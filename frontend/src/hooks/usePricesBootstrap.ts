import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { ApiError } from '../services/apiClient'
import { getPrices } from '../services/api'
import { useMarketStore } from '../store/marketStore'
import { ALL_DATA_SOURCES } from '../types/market'
import type { DataSource, Price } from '../types/market'

async function fetchAllSourcesPrices(): Promise<{ source: DataSource; prices: Price[] }[]> {
  const settled = await Promise.allSettled(
    ALL_DATA_SOURCES.map(async (source) => ({ source, prices: await getPrices(source) })),
  )
  return settled.flatMap((result, index) => {
    if (result.status === 'fulfilled') return [result.value]

    // TradingView 503s when Settings.tradingview_enabled is False -- expected,
    // skip it rather than letting a disabled source fail the whole bootstrap.
    const isUnavailable = result.reason instanceof ApiError && result.reason.status === 503
    if (!isUnavailable) {
      console.warn(`[usePricesBootstrap] ${ALL_DATA_SOURCES[index]} failed`, result.reason)
    }
    return []
  })
}

/** Fetches the latest price for every symbol, for every source, once on
 * mount and seeds the store, so a symbol card shows real data immediately
 * instead of "—" until its first live tick arrives — a lower-liquidity
 * pair (e.g. AUDUSD) can go a while without ticking even though its
 * candles/predictions are already populated. Both sources are fetched
 * regardless of which is currently active, so toggling never needs a
 * refetch. useMarketSocket keeps it live afterward. */
export function usePricesBootstrap(): void {
  const setPrice = useMarketStore((state) => state.setPrice)
  const { data } = useQuery({ queryKey: ['prices', 'latest', 'all-sources'], queryFn: fetchAllSourcesPrices })

  useEffect(() => {
    if (data) {
      for (const { source, prices } of data) {
        for (const price of prices) {
          setPrice(source, price)
        }
      }
    }
  }, [data, setPrice])
}
