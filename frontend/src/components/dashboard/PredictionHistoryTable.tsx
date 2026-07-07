import type { Prediction } from '../../types/prediction'
import { DirectionBadge } from './DirectionBadge'

interface PredictionHistoryTableProps {
  predictions: Prediction[]
}

export function PredictionHistoryTable({ predictions }: PredictionHistoryTableProps) {
  if (predictions.length === 0) {
    return <p className="text-sm text-slate-400">No prediction history for this symbol/timeframe yet.</p>
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-slate-400">
          <th className="pb-2 font-medium">Time</th>
          <th className="pb-2 font-medium">Direction</th>
          <th className="pb-2 font-medium">Confidence</th>
          <th className="pb-2 font-medium">Price</th>
        </tr>
      </thead>
      <tbody>
        {predictions.map((prediction) => (
          <tr key={prediction.timestamp} className="border-t border-slate-800">
            <td className="py-2 text-slate-300">{new Date(prediction.timestamp).toLocaleString()}</td>
            <td className="py-2">
              <DirectionBadge direction={prediction.direction} />
            </td>
            <td className="py-2 text-slate-300">{prediction.confidence.toFixed(0)}%</td>
            <td className="py-2 text-slate-200">{prediction.price.toFixed(5)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
