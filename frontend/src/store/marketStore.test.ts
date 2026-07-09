import { beforeEach, describe, expect, it } from 'vitest'
import type { Signal } from '../types/signal'
import { selectOpenSignals, useMarketStore } from './marketStore'

const INITIAL_STATE = useMarketStore.getState()

beforeEach(() => {
  useMarketStore.setState(INITIAL_STATE, true)
})

function signal(overrides: Partial<Signal> = {}): Signal {
  return {
    id: 1,
    symbol: 'XAUUSD',
    entry_timeframe: '15m',
    direction: 'bullish',
    entry: 100,
    stop: 95,
    target: 115,
    risk_reward: 3,
    status: 'open',
    reason: 'test',
    details: {},
    opened_at: '2026-01-01T00:00:00Z',
    closed_at: null,
    realized_rr: null,
    ...overrides,
  }
}

describe('selectOpenSignals', () => {
  it('excludes resolved signals and sorts open ones most-recently-opened first', () => {
    useMarketStore.getState().upsertSignal('twelve_data', signal({ id: 1, opened_at: '2026-01-01T00:00:00Z' }))
    useMarketStore.getState().upsertSignal('twelve_data', signal({ id: 2, opened_at: '2026-01-02T00:00:00Z' }))
    useMarketStore.getState().upsertSignal('twelve_data', signal({ id: 3, status: 'win', closed_at: '2026-01-03T00:00:00Z' }))

    const open = selectOpenSignals(useMarketStore.getState(), 'twelve_data')

    expect(open.map((s) => s.id)).toEqual([2, 1])
  })

  it('scopes to the requested source only -- a signal in the other source never appears', () => {
    useMarketStore.getState().upsertSignal('twelve_data', signal({ id: 1 }))
    useMarketStore.getState().upsertSignal('tradingview', signal({ id: 2 }))

    expect(selectOpenSignals(useMarketStore.getState(), 'twelve_data').map((s) => s.id)).toEqual([1])
    expect(selectOpenSignals(useMarketStore.getState(), 'tradingview').map((s) => s.id)).toEqual([2])
  })
})

describe('per-source isolation', () => {
  it('setPrice for one source never touches the other source\'s prices', () => {
    useMarketStore
      .getState()
      .setPrice('twelve_data', { symbol: 'XAUUSD', price: 2350, timestamp: '2026-01-01T00:00:00Z' })

    const state = useMarketStore.getState()
    expect(state.prices.twelve_data.XAUUSD?.price).toBe(2350)
    expect(state.prices.tradingview.XAUUSD).toBeUndefined()
  })

  it('setFeedStatus for one source never touches the other source\'s status', () => {
    useMarketStore.getState().setFeedStatus('tradingview', 'live', '2026-01-01T00:00:00Z')

    const state = useMarketStore.getState()
    expect(state.feedStatus.tradingview?.status).toBe('live')
    expect(state.feedStatus.twelve_data).toBeNull()
  })
})

describe('hydrateSignals', () => {
  it('does not overwrite a signal already updated live (live upserts take precedence over a later hydrate)', () => {
    useMarketStore.getState().upsertSignal('twelve_data', signal({ id: 1, status: 'win', realized_rr: 3 }))

    // A bootstrap fetch that started before the live update lands afterward.
    useMarketStore.getState().hydrateSignals('twelve_data', [signal({ id: 1, status: 'open', realized_rr: null })])

    expect(useMarketStore.getState().signals.twelve_data[1]?.status).toBe('win')
  })

  it('adds signals not already present', () => {
    useMarketStore.getState().hydrateSignals('twelve_data', [signal({ id: 1 }), signal({ id: 2 })])

    expect(Object.keys(useMarketStore.getState().signals.twelve_data)).toHaveLength(2)
  })
})
