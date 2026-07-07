import type { Direction, MarketSymbol, Timeframe } from './market'

export type SignalStatus = 'open' | 'win' | 'loss' | 'expired'

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
  opened_at: string
  closed_at: string | null
  realized_rr: number | null
}
