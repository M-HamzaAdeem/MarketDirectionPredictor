import { usePredictionsBootstrap } from '../../hooks/usePredictionsBootstrap'
import { useMarketStore } from '../../store/marketStore'
import { ALL_SYMBOLS, ALL_TIMEFRAMES } from '../../types/market'
import { computeOverall, type OverallCall } from '../../utils/predictionOverall'
import { DirectionBadge } from './DirectionBadge'

const OVERALL_STYLE: Record<OverallCall, string> = {
  bullish: 'bg-emerald-500/15 text-emerald-400',
  bearish: 'bg-red-500/15 text-red-400',
  neutral: 'bg-slate-500/15 text-slate-400',
  mixed: 'bg-amber-500/15 text-amber-400',
}

export function PredictionPanel() {
  usePredictionsBootstrap()

  // Deliberately different from SignalFeed: the selector here reads the
  // stored `predictions` object directly (a stable reference Zustand only
  // replaces on actual change) rather than a derived array, so there's no
  // derived-container-in-selector footgun to guard against with useShallow.
  const predictions = useMarketStore((state) => state.predictions)

  if (Object.keys(predictions).length === 0) {
    return <p className="text-sm text-slate-400">No predictions yet.</p>
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-slate-400">
          <th className="pb-2 font-medium">Symbol</th>
          {ALL_TIMEFRAMES.map((timeframe) => (
            <th key={timeframe} className="pb-2 font-medium">
              {timeframe}
            </th>
          ))}
          <th className="pb-2 font-medium">Overall</th>
        </tr>
      </thead>
      <tbody>
        {ALL_SYMBOLS.map((symbol) => {
          const rowPredictions = ALL_TIMEFRAMES.map((timeframe) => predictions[`${symbol}:${timeframe}`])
          const overall = computeOverall(rowPredictions)

          return (
            <tr key={symbol} className="border-t border-slate-800">
              <td className="py-2 font-medium text-slate-200">{symbol}</td>
              {rowPredictions.map((prediction, index) => (
                <td key={ALL_TIMEFRAMES[index]} className="py-2">
                  {prediction ? (
                    <span className="flex items-center gap-1.5 whitespace-nowrap">
                      <DirectionBadge direction={prediction.direction} />
                      <span className="text-slate-400">{prediction.confidence.toFixed(0)}%</span>
                    </span>
                  ) : (
                    <span className="text-slate-600">—</span>
                  )}
                </td>
              ))}
              <td className="py-2">
                <span className={`rounded px-2 py-0.5 text-xs font-medium uppercase ${OVERALL_STYLE[overall]}`}>
                  {overall}
                </span>
              </td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
