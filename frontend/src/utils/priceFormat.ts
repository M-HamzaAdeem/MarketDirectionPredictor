import type { MarketSymbol } from '../types/market'

// EURUSD/AUDUSD move in increments too small for the default 2-decimal
// price format to show meaningfully; XAUUSD's larger price range is fine
// at the default precision. Single source of truth — PriceChart's visual
// rendering and describeChart's aria-label summary must never disagree
// about how many decimals a symbol quotes to.
const FOUR_DECIMAL_SYMBOLS = new Set<MarketSymbol>(['EURUSD', 'AUDUSD'])

export function pricePrecision(symbol: MarketSymbol): number {
  return FOUR_DECIMAL_SYMBOLS.has(symbol) ? 4 : 2
}
