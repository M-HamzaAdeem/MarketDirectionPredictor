import { describe, expect, it } from 'vitest'
import type { Signal, SignalStatus } from '../types/signal'
import { computePerformanceStats } from './performanceStats'

function makeSignal(status: SignalStatus, realizedRr: number | null): Signal {
  return {
    id: 1,
    symbol: 'XAUUSD',
    entry_timeframe: '15m',
    direction: 'bullish',
    entry: 100,
    stop: 95,
    target: 110,
    risk_reward: 2,
    status,
    reason: 'test',
    details: {},
    opened_at: '2026-01-01T00:00:00Z',
    closed_at: status === 'open' ? null : '2026-01-01T01:00:00Z',
    realized_rr: realizedRr,
  }
}

describe('computePerformanceStats', () => {
  it('returns all zeros and null rates for an empty list', () => {
    const stats = computePerformanceStats([])

    expect(stats.total).toBe(0)
    expect(stats.winRate).toBeNull()
    expect(stats.averageRealizedRiskReward).toBeNull()
  })

  it('counts each status independently', () => {
    const signals = [
      makeSignal('win', 2.0),
      makeSignal('win', 3.0),
      makeSignal('loss', -1.0),
      makeSignal('expired', 0.0),
      makeSignal('open', null),
    ]

    const stats = computePerformanceStats(signals)

    expect(stats.total).toBe(5)
    expect(stats.wins).toBe(2)
    expect(stats.losses).toBe(1)
    expect(stats.expired).toBe(1)
    expect(stats.open).toBe(1)
  })

  it('computes win rate over wins+losses only, excluding expired and open', () => {
    const signals = [makeSignal('win', 2.0), makeSignal('win', 2.0), makeSignal('loss', -1.0), makeSignal('expired', 0.0)]

    const stats = computePerformanceStats(signals)

    // 2 wins / (2 wins + 1 loss) = 0.666...
    expect(stats.winRate).toBeCloseTo(2 / 3)
  })

  it('returns a null win rate when nothing has won or lost yet', () => {
    const stats = computePerformanceStats([makeSignal('open', null), makeSignal('expired', 0.0)])
    expect(stats.winRate).toBeNull()
  })

  it('averages realized R:R across wins and losses only', () => {
    const signals = [makeSignal('win', 3.0), makeSignal('loss', -1.0), makeSignal('expired', 0.0)]

    const stats = computePerformanceStats(signals)

    // (3.0 + -1.0) / 2 = 1.0 -- expired's 0.0 is excluded
    expect(stats.averageRealizedRiskReward).toBeCloseTo(1.0)
  })

  it('counts a win with a null realized_rr toward wins but excludes it from the average', () => {
    const signals = [makeSignal('win', null), makeSignal('win', 4.0)]

    const stats = computePerformanceStats(signals)

    expect(stats.wins).toBe(2)
    // only the 4.0 win has a non-null realized_rr to average
    expect(stats.averageRealizedRiskReward).toBeCloseTo(4.0)
  })
})
