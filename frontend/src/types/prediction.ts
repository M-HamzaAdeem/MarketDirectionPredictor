import type { Direction, MarketSymbol, Timeframe } from './market'

/** Phase 3 rule-based prediction — scores every candle close with a
 * direction/confidence, unlike Signal which only ever exists for a
 * fully-specified, R:R-gated ICT trade setup. */
export interface Prediction {
  symbol: MarketSymbol
  timeframe: Timeframe
  direction: Direction
  confidence: number
  reason: string
  price: number
  timestamp: string
}
