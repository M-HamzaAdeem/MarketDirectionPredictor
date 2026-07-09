// Field names in this file intentionally match the backend's wire format
// (snake_case) exactly, rather than being transformed to camelCase, to
// avoid a hand-maintained mapping layer that could silently drift out of
// sync with the API as fields change.

export type MarketSymbol = 'XAUUSD' | 'EURUSD' | 'AUDUSD'

export type Timeframe = '1m' | '5m' | '15m' | '1h' | '4h' | '1d' | '1w'

// The enumerable form of the two union types above, for callers that need
// to iterate every value (e.g. seeding a bootstrap fetch per symbol x
// timeframe) rather than just type-check one. A single source so this
// list can't drift out of sync across the three places that need it.
export const ALL_SYMBOLS = ['XAUUSD', 'EURUSD', 'AUDUSD'] as const satisfies readonly MarketSymbol[]

export const ALL_TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d', '1w'] as const satisfies readonly Timeframe[]

export type Direction = 'bullish' | 'bearish' | 'neutral'

export type FeedStatus = 'mock' | 'live' | 'degraded' | 'disconnected'

// Which of the two fully independent backend pipelines a piece of data
// came from — Twelve Data and TradingView run simultaneously, each with
// its own tables, so this is never inferred, only read off the wire.
export type DataSource = 'twelve_data' | 'tradingview'

export const ALL_DATA_SOURCES = ['twelve_data', 'tradingview'] as const satisfies readonly DataSource[]

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
