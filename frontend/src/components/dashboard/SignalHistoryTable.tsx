import type { Signal } from '../../types/signal'
import { DirectionBadge } from './DirectionBadge'
import { SignalStatusBadge } from './SignalStatusBadge'

interface SignalHistoryTableProps {
  signals: Signal[]
}

export function SignalHistoryTable({ signals }: SignalHistoryTableProps) {
  if (signals.length === 0) {
    return <p className="text-sm text-slate-400">No signal history for this symbol yet.</p>
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-slate-400">
          <th className="pb-2 font-medium">Opened</th>
          <th className="pb-2 font-medium">Direction</th>
          <th className="pb-2 font-medium">Entry</th>
          <th className="pb-2 font-medium">R:R</th>
          <th className="pb-2 font-medium">Status</th>
          <th className="pb-2 font-medium">Realized R:R</th>
        </tr>
      </thead>
      <tbody>
        {signals.map((signal) => (
          <tr key={signal.id} className="border-t border-slate-800">
            <td className="py-2 text-slate-300">{new Date(signal.opened_at).toLocaleString()}</td>
            <td className="py-2">
              <DirectionBadge direction={signal.direction} />
            </td>
            <td className="py-2 text-slate-200">{signal.entry.toFixed(5)}</td>
            <td className="py-2 text-slate-300">{signal.risk_reward.toFixed(2)}</td>
            <td className="py-2">
              <SignalStatusBadge status={signal.status} />
            </td>
            <td className="py-2 text-slate-300">
              {signal.realized_rr === null ? '—' : signal.realized_rr.toFixed(2)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
