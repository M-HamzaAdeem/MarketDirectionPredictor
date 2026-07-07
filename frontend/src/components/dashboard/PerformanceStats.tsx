import { computePerformanceStats } from '../../utils/performanceStats'
import type { Signal } from '../../types/signal'

interface PerformanceStatsProps {
  signals: Signal[]
}

export function PerformanceStats({ signals }: PerformanceStatsProps) {
  const stats = computePerformanceStats(signals)

  return (
    <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div>
        <dt className="text-sm text-slate-400">Win rate</dt>
        <dd className="text-xl font-semibold text-slate-100">
          {stats.winRate === null ? '—' : `${(stats.winRate * 100).toFixed(0)}%`}
        </dd>
      </div>
      <div>
        <dt className="text-sm text-slate-400">Avg realized R:R</dt>
        <dd className="text-xl font-semibold text-slate-100">
          {stats.averageRealizedRiskReward === null ? '—' : stats.averageRealizedRiskReward.toFixed(2)}
        </dd>
      </div>
      <div>
        <dt className="text-sm text-slate-400">Wins / Losses</dt>
        <dd className="text-xl font-semibold text-slate-100">
          {stats.wins} / {stats.losses}
        </dd>
      </div>
      <div>
        <dt className="text-sm text-slate-400">Total signals</dt>
        <dd className="text-xl font-semibold text-slate-100">{stats.total}</dd>
      </div>
    </dl>
  )
}
