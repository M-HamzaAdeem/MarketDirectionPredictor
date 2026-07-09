import { create } from 'zustand'
import { useShallow } from 'zustand/react/shallow'
import type { DataSource, FeedStatus, MarketSymbol, Price } from '../types/market'
import type { Prediction } from '../types/prediction'
import type { Signal } from '../types/signal'

interface FeedStatusState {
  status: FeedStatus
  timestamp: string
}

type BySource<T> = Record<DataSource, T>

function emptyBySource<T>(makeEmpty: () => T): BySource<T> {
  return { twelve_data: makeEmpty(), tradingview: makeEmpty() }
}

interface MarketState {
  /** Which source's data the dashboard currently displays — both
   * pipelines run continuously in the backend regardless of this. */
  activeSource: DataSource
  feedStatus: BySource<FeedStatusState | null>
  prices: BySource<Partial<Record<MarketSymbol, Price>>>
  /** keyed by `${symbol}:${timeframe}` */
  predictions: BySource<Record<string, Prediction>>
  /** keyed by signal id — both new-open and later resolution updates land here */
  signals: BySource<Record<number, Signal>>

  setActiveSource: (source: DataSource) => void
  setFeedStatus: (source: DataSource, status: FeedStatus, timestamp: string) => void
  setPrice: (source: DataSource, price: Price) => void
  setPrediction: (source: DataSource, prediction: Prediction) => void
  upsertSignal: (source: DataSource, signal: Signal) => void
  hydrateSignals: (source: DataSource, signals: Signal[]) => void
}

export const useMarketStore = create<MarketState>((set) => ({
  // Matches the backend's default source (Settings.tradingview_enabled
  // defaults True) — TradingView needs no API key, so it's the pipeline
  // that works out of the box on a fresh clone.
  activeSource: 'tradingview',
  feedStatus: emptyBySource(() => null),
  prices: emptyBySource(() => ({})),
  predictions: emptyBySource(() => ({})),
  signals: emptyBySource(() => ({})),

  setActiveSource: (source) => set({ activeSource: source }),

  setFeedStatus: (source, status, timestamp) =>
    set((state) => ({ feedStatus: { ...state.feedStatus, [source]: { status, timestamp } } })),

  setPrice: (source, price) =>
    set((state) => ({
      prices: { ...state.prices, [source]: { ...state.prices[source], [price.symbol]: price } },
    })),

  setPrediction: (source, prediction) =>
    set((state) => ({
      predictions: {
        ...state.predictions,
        [source]: {
          ...state.predictions[source],
          [`${prediction.symbol}:${prediction.timeframe}`]: prediction,
        },
      },
    })),

  upsertSignal: (source, signal) =>
    set((state) => ({
      signals: { ...state.signals, [source]: { ...state.signals[source], [signal.id]: signal } },
    })),

  hydrateSignals: (source, signals) =>
    set((state) => ({
      signals: {
        ...state.signals,
        [source]: { ...Object.fromEntries(signals.map((s) => [s.id, s])), ...state.signals[source] },
      },
    })),
}))

/**
 * Open signals for `source`, most-recently-opened first.
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
export function selectOpenSignals(state: MarketState, source: DataSource): Signal[] {
  return Object.values(state.signals[source])
    .filter((signal) => signal.status === 'open')
    .sort((a, b) => b.opened_at.localeCompare(a.opened_at))
}

// Derived selector hooks reading whichever source is currently active, so
// most components change one import line instead of threading a `source`
// prop through themselves and remembering to index by `activeSource`.
// Only `useActiveOpenSignals` needs `useShallow` — the others are plain
// property lookups into an already-stored object, not a per-call
// filter/map/sort derivation, so they're referentially stable as-is.

export function useActiveFeedStatus(): FeedStatusState | null {
  return useMarketStore((state) => state.feedStatus[state.activeSource])
}

export function useActivePrices(): Partial<Record<MarketSymbol, Price>> {
  return useMarketStore((state) => state.prices[state.activeSource])
}

export function useActivePredictions(): Record<string, Prediction> {
  return useMarketStore((state) => state.predictions[state.activeSource])
}

export function useActiveSignals(): Record<number, Signal> {
  return useMarketStore((state) => state.signals[state.activeSource])
}

export function useActiveOpenSignals(): Signal[] {
  return useMarketStore(useShallow((state) => selectOpenSignals(state, state.activeSource)))
}
