// Field names in this file intentionally match the backend's wire format
// (snake_case) exactly, rather than being transformed to camelCase, to
// avoid a hand-maintained mapping layer that could silently drift out of
// sync with the API as fields change.

export type MarketSymbol = 'XAUUSD' | 'EURUSD' | 'AUDUSD'

export type Timeframe = '1m' | '5m' | '15m' | '1h' | '4h'

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
