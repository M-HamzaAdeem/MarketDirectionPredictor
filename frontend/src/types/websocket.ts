import type { Direction, FeedStatus, MarketSymbol, Timeframe } from './market'
import type { SignalDetails, SignalStatus } from './signal'

export interface PriceMessage {
  type: 'price'
  symbol: MarketSymbol
  price: number
  timestamp: string
}

export interface PredictionMessage {
  type: 'prediction'
  symbol: MarketSymbol
  timeframe: Timeframe
  direction: Direction
  confidence: number
  reason: string
  price: number
  timestamp: string
}

export interface FeedStatusMessage {
  type: 'feed_status'
  status: FeedStatus
  timestamp: string
}

/** Broadcast both when a signal opens (status "open") and again whenever
 * the backend's SignalTracker resolves it (status "win"/"loss"/"expired")
 * — dispatch on `id` to know whether to add a new entry or update one
 * already held. */
export interface SignalMessage {
  type: 'signal'
  id: number
  symbol: MarketSymbol
  entry_timeframe: Timeframe
  direction: Direction
  entry: number
  stop: number
  target: number
  risk_reward: number
  reason: string
  details: SignalDetails
  status: SignalStatus
  opened_at: string
  closed_at: string | null
  realized_rr: number | null
}

export type WebSocketMessage = PriceMessage | PredictionMessage | FeedStatusMessage | SignalMessage
