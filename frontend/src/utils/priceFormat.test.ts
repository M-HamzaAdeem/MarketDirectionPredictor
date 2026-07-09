import { describe, expect, it } from 'vitest'
import { pricePrecision } from './priceFormat'

describe('pricePrecision', () => {
  it('returns 4 decimals for EURUSD and AUDUSD', () => {
    expect(pricePrecision('EURUSD')).toBe(4)
    expect(pricePrecision('AUDUSD')).toBe(4)
  })

  it('returns 2 decimals for XAUUSD', () => {
    expect(pricePrecision('XAUUSD')).toBe(2)
  })
})
