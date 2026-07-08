// Field names in this file intentionally match the backend's wire format
// (snake_case) exactly, rather than being transformed to camelCase, to
// avoid a hand-maintained mapping layer that could silently drift out of
// sync with the API as fields change.

export type MarketSymbol = 'XAUUSD' | 'EURUSD' | 'AUDUSD'

export type Timeframe = '1m' | '5m' | '15m' | '1h' | '4h'

// The enumerable form of the two union types above, for callers that need
// to iterate every value (e.g. seeding a bootstrap fetch per symbol x
// timeframe) rather than just type-check one. A single source so this
// list can't drift out of sync across the three places that need it.
export const ALL_SYMBOLS = ['XAUUSD', 'EURUSD', 'AUDUSD'] as const satisfies readonly MarketSymbol[]

export const ALL_TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h'] as const satisfies readonly Timeframe[]

export type Direction = 'bullish' | 'bearish' | 'neutral'

export type FeedStatus = 'mock' | 'live' | 'degraded' | 'disconnected'

export interface Candle {
  open_time: string
  close_time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface Price {
  symbol: MarketSymbol
  price: number
  timestamp: string
}
