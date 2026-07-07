import type { Direction } from '../../types/market'

const DIRECTION_STYLE: Record<Direction, string> = {
  bullish: 'bg-emerald-500/15 text-emerald-400',
  bearish: 'bg-red-500/15 text-red-400',
  neutral: 'bg-slate-500/15 text-slate-400',
}

export function DirectionBadge({ direction }: { direction: Direction }) {
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium uppercase ${DIRECTION_STYLE[direction]}`}>
      {direction}
    </span>
  )
}
