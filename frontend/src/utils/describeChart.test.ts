import { describe, expect, it } from 'vitest'
import type { Candle } from '../types/market'
import { describeChart } from './describeChart'

function makeCandle(close: number): Candle {
  return {
    open_time: '2026-01-01T00:00:00Z',
    close_time: '2026-01-01T00:15:00Z',
    open: close,
    high: close,
    low: close,
    close,
    volume: 0,
  }
}

describe('describeChart', () => {
  it('reports no candles loaded yet when the list is empty', () => {
    expect(describeChart('XAUUSD', '15m', [])).toBe('Candlestick chart for XAUUSD 15m, no candles loaded yet')
  })

  it('uses singular "candle" for exactly one candle', () => {
    expect(describeChart('XAUUSD', '15m', [makeCandle(4071.827)])).toBe(
      'Candlestick chart for XAUUSD 15m, 1 candle, current price 4071.83',
    )
  })

  it('uses plural "candles" and the latest (last) candle\'s close for more than one', () => {
    expect(describeChart('XAUUSD', '1h', [makeCandle(100), makeCandle(102.5)])).toBe(
      'Candlestick chart for XAUUSD 1h, 2 candles, current price 102.50',
    )
  })

  it('formats EURUSD/AUDUSD to 4 decimal places instead of the default 2', () => {
    expect(describeChart('EURUSD', '5m', [makeCandle(1.140625)])).toBe(
      'Candlestick chart for EURUSD 5m, 1 candle, current price 1.1406',
    )
    expect(describeChart('AUDUSD', '5m', [makeCandle(0.691095)])).toBe(
      'Candlestick chart for AUDUSD 5m, 1 candle, current price 0.6911',
    )
  })
})
