import type { Signal } from '../../types/signal'
import { DirectionBadge } from './DirectionBadge'
import { SignalStatusBadge } from './SignalStatusBadge'

export function SignalCard({ signal }: { signal: Signal }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-100">{signal.symbol}</span>
          <DirectionBadge direction={signal.direction} />
        </div>
        <SignalStatusBadge status={signal.status} />
      </div>

      <dl className="mt-3 grid grid-cols-3 gap-2 text-sm">
        <div>
          <dt className="text-slate-400">Entry</dt>
          <dd className="text-slate-200">{signal.entry.toFixed(5)}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Stop</dt>
          <dd className="text-red-400">{signal.stop.toFixed(5)}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Target</dt>
          <dd className="text-emerald-400">{signal.target.toFixed(5)}</dd>
        </div>
      </dl>

      <div className="mt-2 text-sm text-slate-400">R:R {signal.risk_reward.toFixed(2)}</div>
      <p className="mt-2 text-xs text-slate-400">{signal.reason}</p>

      {signal.status !== 'open' && signal.realized_rr !== null && (
        <p className="mt-2 text-xs font-medium text-slate-400">Realized R:R {signal.realized_rr.toFixed(2)}</p>
      )}
    </div>
  )
}
