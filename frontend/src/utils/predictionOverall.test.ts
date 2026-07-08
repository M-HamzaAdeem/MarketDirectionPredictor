import { describe, expect, it } from 'vitest'
import type { Prediction } from '../types/prediction'
import { computeOverall } from './predictionOverall'

function makePrediction(direction: Prediction['direction'], confidence = 50): Prediction {
  return {
    symbol: 'XAUUSD',
    timeframe: '1m',
    direction,
    confidence,
    reason: 'test',
    price: 100,
    timestamp: '2026-01-01T00:00:00Z',
  }
}

describe('computeOverall', () => {
  it('calls bullish when it leads bearish by more than one vote', () => {
    const row = [
      makePrediction('bullish'),
      makePrediction('bullish'),
      makePrediction('bullish'),
      makePrediction('bearish'),
      makePrediction('neutral'),
    ]
    expect(computeOverall(row)).toBe('bullish')
  })

  it('calls bearish when it leads bullish by more than one vote', () => {
    const row = [
      makePrediction('bullish'),
      makePrediction('bearish'),
      makePrediction('bearish'),
      makePrediction('bearish'),
      makePrediction('bearish'),
    ]
    expect(computeOverall(row)).toBe('bearish')
  })

  it('calls mixed when the lead is only a single vote', () => {
    const row = [
      makePrediction('bearish'),
      makePrediction('bullish'),
      makePrediction('bullish'),
      makePrediction('bearish'),
      makePrediction('bearish'),
    ]
    expect(computeOverall(row)).toBe('mixed')
  })

  it('calls mixed on an exact tie', () => {
    const row = [makePrediction('bullish'), makePrediction('bullish'), makePrediction('bearish'), makePrediction('bearish')]
    expect(computeOverall(row)).toBe('mixed')
  })

  it('calls mixed when every timeframe is neutral or missing', () => {
    const row = [makePrediction('neutral'), makePrediction('neutral'), undefined, undefined, undefined]
    expect(computeOverall(row)).toBe('mixed')
  })

  it('treats missing predictions as neither bullish nor bearish', () => {
    const row = [makePrediction('bullish'), makePrediction('bullish'), makePrediction('bullish'), undefined, undefined]
    expect(computeOverall(row)).toBe('bullish')
  })
})
