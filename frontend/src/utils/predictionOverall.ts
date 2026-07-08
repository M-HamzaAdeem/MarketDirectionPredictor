import type { Direction } from '../types/market'
import type { Prediction } from '../types/prediction'

export type OverallCall = Direction | 'mixed'

// A direction only earns the Overall call once it leads the other by more
// than one timeframe's vote — a 3-vs-2 split across 5 timeframes is real
// disagreement, not noise to smooth over into a false consensus.
const OVERALL_MARGIN_THRESHOLD = 1

export function computeOverall(rowPredictions: (Prediction | undefined)[]): OverallCall {
  const bullish = rowPredictions.filter((prediction) => prediction?.direction === 'bullish').length
  const bearish = rowPredictions.filter((prediction) => prediction?.direction === 'bearish').length

  if (bullish > bearish + OVERALL_MARGIN_THRESHOLD) return 'bullish'
  if (bearish > bullish + OVERALL_MARGIN_THRESHOLD) return 'bearish'
  return 'mixed'
}
