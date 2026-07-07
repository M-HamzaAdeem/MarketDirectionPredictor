import { create } from 'zustand'
import type { FeedStatus, MarketSymbol, Price } from '../types/market'
import type { Prediction } from '../types/prediction'
import type { Signal } from '../types/signal'

interface FeedStatusState {
  status: FeedStatus
  timestamp: string
}

interface MarketState {
  feedStatus: FeedStatusState | null
  prices: Partial<Record<MarketSymbol, Price>>
  /** keyed by `${symbol}:${timeframe}` */
  predictions: Record<string, Prediction>
  /** keyed by signal id — both new-open and later resolution updates land here */
  signals: Record<number, Signal>

  setFeedStatus: (status: FeedStatus, timestamp: string) => void
  setPrice: (price: Price) => void
  setPrediction: (prediction: Prediction) => void
  upsertSignal: (signal: Signal) => void
  hydrateSignals: (signals: Signal[]) => void
}

export const useMarketStore = create<MarketState>((set) => ({
  feedStatus: null,
  prices: {},
  predictions: {},
  signals: {},

  setFeedStatus: (status, timestamp) => set({ feedStatus: { status, timestamp } }),

  setPrice: (price) => set((state) => ({ prices: { ...state.prices, [price.symbol]: price } })),

  setPrediction: (prediction) =>
    set((state) => ({
      predictions: { ...state.predictions, [`${prediction.symbol}:${prediction.timeframe}`]: prediction },
    })),

  upsertSignal: (signal) => set((state) => ({ signals: { ...state.signals, [signal.id]: signal } })),

  hydrateSignals: (signals) =>
    set((state) => ({ signals: { ...Object.fromEntries(signals.map((s) => [s.id, s])), ...state.signals } })),
}))

/**
 * Open signals, most-recently-opened first.
 *
 * @remarks Returns a new array on every call (filter + sort). Every call
 * site MUST wrap this in `useShallow` from `zustand/react/shallow`, or
 * React's `useSyncExternalStore` sees a "changed" snapshot on every render
 * and infinite-loops — see decisions.md, "Zustand selector gotcha."
 *
 * The sort relies on `opened_at` being a sortable ISO-8601 UTC string (as
 * the backend always emits) — `localeCompare` would silently misorder a
 * timestamp with a non-UTC offset or non-padded fields.
 */
export function selectOpenSignals(state: MarketState): Signal[] {
  return Object.values(state.signals)
    .filter((signal) => signal.status === 'open')
    .sort((a, b) => b.opened_at.localeCompare(a.opened_at))
}
