import { AppShell } from '../components/layout/AppShell'
import { useConfig } from '../hooks/useConfig'
import type { Config } from '../types/config'

function SettingsGrid({ items }: { items: [string, string | number][] }) {
  return (
    <dl className="grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt className="text-sm text-slate-400">{label}</dt>
          <dd className="text-slate-100">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

function feedItems(config: Config): [string, string | number][] {
  return [
    ['Provider', config.feed_provider],
    ['Mock time acceleration', `${config.mock_time_acceleration}x`],
    ['Symbols', config.symbols.join(', ')],
    ['Timeframes', config.timeframes.join(', ')],
  ]
}

function predictionStrategyItems(config: Config): [string, string | number][] {
  return [['Active strategy', config.prediction_strategy]]
}

function signalPipelineItems(config: Config): [string, string | number][] {
  return [
    ['Minimum R:R', config.min_risk_reward.toFixed(2)],
    ['OTE zone', `${(config.ote_shallow_ratio * 100).toFixed(1)}%–${(config.ote_deep_ratio * 100).toFixed(1)}%`],
    ['Stop ATR buffer', `${config.stop_atr_buffer_multiplier}x ATR`],
    ['Impulse ATR multiplier', `${config.impulse_atr_multiplier}x ATR`],
    ['Signal expiry', `${config.signal_expiry_days} days`],
  ]
}

function ruleBasedItems(config: Config): [string, string | number][] {
  return [
    ['RSI bullish threshold', config.rsi_bullish_threshold.toFixed(0)],
    ['RSI bearish threshold', config.rsi_bearish_threshold.toFixed(0)],
    ['SMA fast / slow period', `${config.sma_fast_period} / ${config.sma_slow_period}`],
    ['RSI period', config.rsi_period],
    ['ATR period', config.atr_period],
    ['Momentum period', config.momentum_period],
    ['Volatility period', config.volatility_period],
  ]
}

export function SettingsPage() {
  const { data: config, isLoading, isError } = useConfig()

  return (
    <AppShell>
      <p className="text-sm text-slate-400">
        Read-only — these values are loaded once when the backend starts, and the strategy thresholds below are
        plain code constants, not persisted config. See docs/architecture.md's Phase 7 note for what live editing
        would require.
      </p>

      {isLoading && <p className="text-sm text-slate-400">Loading configuration…</p>}
      {isError && <p className="text-sm text-red-400">Could not load configuration.</p>}

      {config && (
        <>
          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">Feed</h2>
            <SettingsGrid items={feedItems(config)} />
          </section>

          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">Prediction</h2>
            <SettingsGrid items={predictionStrategyItems(config)} />
          </section>

          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
              ICT Signal Pipeline
            </h2>
            <SettingsGrid items={signalPipelineItems(config)} />
          </section>

          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
              Rule-Based Prediction Thresholds
            </h2>
            <p className="mb-3 text-sm text-slate-400">
              Shown for reference; applied only when the active strategy above is rule_based.
            </p>
            <SettingsGrid items={ruleBasedItems(config)} />
          </section>
        </>
      )}
    </AppShell>
  )
}
