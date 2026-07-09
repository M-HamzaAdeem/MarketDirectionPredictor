import type { Direction } from '../types/market'

/** How far price has moved from entry toward stop (-1R) or target
 * (signal.risk_reward R), expressed in the same R-multiple unit as
 * risk_reward itself so "Current" and "R:R" are directly comparable —
 * 0 at entry, -1 at stop, +risk_reward at target. Returns null if risk
 * is zero (entry == stop, shouldn't happen for a real signal) or
 * direction is 'neutral' (signals are never neutral; guards the shared
 * Direction type, not a real case). */
export function computeCurrentRiskReward(
  direction: Direction,
  entry: number,
  stop: number,
  currentPrice: number,
): number | null {
  if (direction === 'neutral') return null

  const risk = Math.abs(entry - stop)
  if (risk === 0) return null

  const signedMove = direction === 'bullish' ? currentPrice - entry : entry - currentPrice
  return signedMove / risk
}
