import type { SignalStatus } from '../../types/signal'

const STATUS_STYLE: Record<SignalStatus, string> = {
  open: 'bg-blue-500/15 text-blue-400',
  win: 'bg-emerald-500/15 text-emerald-400',
  loss: 'bg-red-500/15 text-red-400',
  expired: 'bg-slate-500/15 text-slate-400',
}

export function SignalStatusBadge({ status }: { status: SignalStatus }) {
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium uppercase ${STATUS_STYLE[status]}`}>{status}</span>
  )
}
