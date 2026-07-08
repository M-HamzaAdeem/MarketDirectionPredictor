import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { getPrices } from '../services/api'
import { useMarketStore } from '../store/marketStore'

/** Fetches the latest price for every symbol once on mount and seeds the
 * store, so a symbol card shows real data immediately instead of "—" until
 * its first live tick arrives — a lower-liquidity pair (e.g. AUDUSD) can go
 * a while without ticking even though its candles/predictions are already
 * populated. useMarketSocket keeps it live afterward. */
export function usePricesBootstrap(): void {
  const setPrice = useMarketStore((state) => state.setPrice)
  const { data } = useQuery({ queryKey: ['prices', 'latest'], queryFn: getPrices })

  useEffect(() => {
    if (data) {
      for (const price of data) {
        setPrice(price)
      }
    }
  }, [data, setPrice])
}
