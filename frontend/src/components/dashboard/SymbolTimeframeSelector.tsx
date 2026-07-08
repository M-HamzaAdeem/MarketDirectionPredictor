import { ALL_SYMBOLS, ALL_TIMEFRAMES, type MarketSymbol, type Timeframe } from '../../types/market'

interface SymbolTimeframeSelectorProps {
  symbol: MarketSymbol
  timeframe: Timeframe
  onSymbolChange: (symbol: MarketSymbol) => void
  onTimeframeChange: (timeframe: Timeframe) => void
}

export function SymbolTimeframeSelector({
  symbol,
  timeframe,
  onSymbolChange,
  onTimeframeChange,
}: SymbolTimeframeSelectorProps) {
  return (
    <div className="flex items-center gap-3">
      <label className="flex items-center gap-2 text-sm text-slate-400">
        Symbol
        <select
          value={symbol}
          onChange={(event) => onSymbolChange(event.target.value as MarketSymbol)}
          className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-slate-100"
        >
          {ALL_SYMBOLS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-2 text-sm text-slate-400">
        Timeframe
        <select
          value={timeframe}
          onChange={(event) => onTimeframeChange(event.target.value as Timeframe)}
          className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-slate-100"
        >
          {ALL_TIMEFRAMES.map((tf) => (
            <option key={tf} value={tf}>
              {tf}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}
