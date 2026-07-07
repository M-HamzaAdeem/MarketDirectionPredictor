import type { Signal } from '../types/signal'

export interface PerformanceStats {
  total: number
  wins: number
  losses: number
  expired: number
  open: number
  /** wins / (wins + losses); null if neither has happened yet — expired
   * signals are excluded, since they never resolved to a clear outcome. */
  winRate: number | null
  /** average realized_rr across resolved WIN/LOSS signals; null if none yet. */
  averageRealizedRiskReward: number | null
}

export function computePerformanceStats(signals: Signal[]): PerformanceStats {
  const wins = signals.filter((signal) => signal.status === 'win')
  const losses = signals.filter((signal) => signal.status === 'loss')
  const expired = signals.filter((signal) => signal.status === 'expired')
  const open = signals.filter((signal) => signal.status === 'open')

  const decided = wins.length + losses.length
  const resolvedRiskRewards = [...wins, ...losses]
    .map((signal) => signal.realized_rr)
    .filter((value): value is number => value !== null)

  return {
    total: signals.length,
    wins: wins.length,
    losses: losses.length,
    expired: expired.length,
    open: open.length,
    winRate: decided > 0 ? wins.length / decided : null,
    averageRealizedRiskReward:
      resolvedRiskRewards.length > 0
        ? resolvedRiskRewards.reduce((sum, value) => sum + value, 0) / resolvedRiskRewards.length
        : null,
  }
}
