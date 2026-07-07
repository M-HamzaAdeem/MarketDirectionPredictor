import { useMarketStore } from '../../store/marketStore'
import { DirectionBadge } from './DirectionBadge'

export function PredictionPanel() {
  // Deliberately different from SignalFeed: the selector here reads the
  // stored `predictions` object directly (a stable reference Zustand only
  // replaces on actual change), and the sort happens in the render body,
  // not inside the selector — so there's no derived-container-in-selector
  // footgun to guard against with useShallow. Don't "clean this up" into a
  // selectSortedPredictions selector without adding useShallow at every
  // call site if you do.
  const predictions = useMarketStore((state) => state.predictions)
  const rows = Object.values(predictions).sort(
    (a, b) => a.symbol.localeCompare(b.symbol) || a.timeframe.localeCompare(b.timeframe),
  )

  if (rows.length === 0) {
    return <p className="text-sm text-slate-400">No predictions yet.</p>
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-slate-400">
          <th className="pb-2 font-medium">Symbol</th>
          <th className="pb-2 font-medium">TF</th>
          <th className="pb-2 font-medium">Direction</th>
          <th className="pb-2 font-medium">Confidence</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((prediction) => (
          <tr key={`${prediction.symbol}:${prediction.timeframe}`} className="border-t border-slate-800">
            <td className="py-2 text-slate-200">{prediction.symbol}</td>
            <td className="py-2 text-slate-400">{prediction.timeframe}</td>
            <td className="py-2">
              <DirectionBadge direction={prediction.direction} />
            </td>
            <td className="py-2 text-slate-300">{prediction.confidence.toFixed(0)}%</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
