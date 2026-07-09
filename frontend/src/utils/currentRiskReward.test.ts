import { describe, expect, it } from 'vitest'
import { computeCurrentRiskReward } from './currentRiskReward'

describe('computeCurrentRiskReward', () => {
  it('returns 0 right at entry', () => {
    expect(computeCurrentRiskReward('bullish', 100, 95, 100)).toBe(0)
    expect(computeCurrentRiskReward('bearish', 100, 105, 100)).toBe(0)
  })

  it('returns -1 exactly at the stop', () => {
    expect(computeCurrentRiskReward('bullish', 100, 95, 95)).toBe(-1)
    expect(computeCurrentRiskReward('bearish', 100, 105, 105)).toBe(-1)
  })

  it('returns the full risk_reward multiple exactly at the target', () => {
    // entry 100, stop 95 -> risk 5; target 112 -> reward 12 -> 2.4R
    expect(computeCurrentRiskReward('bullish', 100, 95, 112)).toBeCloseTo(2.4)
    expect(computeCurrentRiskReward('bearish', 100, 105, 88)).toBeCloseTo(2.4)
  })

  it('is negative (partial loss) when price has moved partway toward stop', () => {
    expect(computeCurrentRiskReward('bullish', 100, 95, 97.5)).toBeCloseTo(-0.5)
    expect(computeCurrentRiskReward('bearish', 100, 105, 102.5)).toBeCloseTo(-0.5)
  })

  it('is positive (partial profit) when price has moved partway toward target', () => {
    expect(computeCurrentRiskReward('bullish', 100, 95, 103)).toBeCloseTo(0.6)
    expect(computeCurrentRiskReward('bearish', 100, 105, 97)).toBeCloseTo(0.6)
  })

  it('returns null when entry and stop are identical (zero risk)', () => {
    expect(computeCurrentRiskReward('bullish', 100, 100, 105)).toBeNull()
  })

  it('returns null for a neutral direction', () => {
    expect(computeCurrentRiskReward('neutral', 100, 95, 103)).toBeNull()
  })
})
