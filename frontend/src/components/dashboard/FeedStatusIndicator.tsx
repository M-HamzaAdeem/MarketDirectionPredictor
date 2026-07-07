import { useMarketStore } from '../../store/marketStore'
import type { FeedStatus } from '../../types/market'

const STATUS_LABEL: Record<FeedStatus, string> = {
  mock: 'Mock feed',
  live: 'Live feed',
  degraded: 'Degraded',
  disconnected: 'Disconnected',
}

const STATUS_COLOR: Record<FeedStatus, string> = {
  mock: 'bg-amber-400',
  live: 'bg-emerald-400',
  degraded: 'bg-orange-500',
  disconnected: 'bg-red-500',
}

export function FeedStatusIndicator() {
  const feedStatus = useMarketStore((state) => state.feedStatus)

  if (!feedStatus) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <span aria-hidden="true" className="h-2 w-2 rounded-full bg-slate-500" />
        Connecting…
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2 text-sm text-slate-300">
      <span aria-hidden="true" className={`h-2 w-2 rounded-full ${STATUS_COLOR[feedStatus.status]}`} />
      {STATUS_LABEL[feedStatus.status]}
    </div>
  )
}
