import type { MarketSymbol, Timeframe } from './market'

/** Read-only mirror of the backend's ConfigOut — there is no PUT/PATCH,
 * since Settings is loaded once at process startup and the strategy
 * constants aren't configurable at runtime yet. */
export interface Config {
  feed_provider: string
  mock_time_acceleration: number
  symbols: MarketSymbol[]
  timeframes: Timeframe[]
  /** Whether the second, independent TradingView pipeline is running —
   * gates whether SourceToggle is shown at all. */
  tradingview_enabled: boolean

  min_risk_reward: number
  ote_shallow_ratio: number
  ote_deep_ratio: number
  stop_atr_buffer_multiplier: number
  impulse_atr_multiplier: number
  signal_expiry_days: number

  prediction_strategy: string

  rsi_bullish_threshold: number
  rsi_bearish_threshold: number
  sma_fast_period: number
  sma_slow_period: number
  rsi_period: number
  atr_period: number
  momentum_period: number
  volatility_period: number
}
