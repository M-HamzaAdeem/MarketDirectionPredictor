import { useConfig } from '../../hooks/useConfig'
import { useMarketStore } from '../../store/marketStore'
import type { DataSource } from '../../types/market'

const SOURCE_LABEL: Record<DataSource, string> = {
  twelve_data: 'Twelve Data',
  tradingview: 'TradingView',
}

const BASE_BUTTON_CLASS = 'rounded px-2 py-1 text-xs font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-400'

/** Only rendered when the backend actually runs the second pipeline
 * (Settings.tradingview_enabled) — otherwise there's nothing to toggle
 * between, so showing this would be misleading. Both pipelines run
 * continuously regardless of which is selected here; this only changes
 * which one's prices/predictions/signals/chart the dashboard displays. */
export function SourceToggle() {
  const { data: config } = useConfig()
  const activeSource = useMarketStore((state) => state.activeSource)
  const setActiveSource = useMarketStore((state) => state.setActiveSource)

  if (!config?.tradingview_enabled) {
    return null
  }

  return (
    <div className="flex items-center gap-1 rounded-md border border-slate-800 bg-slate-900 p-1">
      {(['twelve_data', 'tradingview'] as const).map((source) => (
        <button
          key={source}
          type="button"
          onClick={() => setActiveSource(source)}
          aria-pressed={activeSource === source}
          className={`${BASE_BUTTON_CLASS} ${
            activeSource === source ? 'bg-sky-500/20 text-sky-300' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          {SOURCE_LABEL[source]}
        </button>
      ))}
    </div>
  )
}
