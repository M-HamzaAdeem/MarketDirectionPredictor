import type { Direction, MarketSymbol, Timeframe } from './market'

export type SignalStatus = 'open' | 'win' | 'loss' | 'expired'

/** Structured breakdown from signal_builder.py's _build_details — every
 * field is optional because it's a free-form JSON blob on the backend
 * (deliberately not promoted to real columns yet; see decisions.md). */
export interface SignalDetails {
  poi_type?: string
  ote_low?: number
  ote_high?: number
  swept_level?: number
  volume_profile_poc?: number | null
  confirming_event?: string
}

/** An ICT trade setup: entry/stop/target/R:R plus full reasoning. Only
 * ever created once every stage of the signal-builder pipeline confirms
 * and R:R clears the project's floor — see docs/signal-method.md. */
export interface Signal {
  id: number
  symbol: MarketSymbol
  entry_timeframe: Timeframe
  direction: Direction
  entry: number
  stop: number
  target: number
  risk_reward: number
  status: SignalStatus
  reason: string
  details: SignalDetails
  opened_at: string
  closed_at: string | null
  realized_rr: number | null
}
