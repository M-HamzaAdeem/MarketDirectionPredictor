import { useSignalsBootstrap } from '../../hooks/useSignalsBootstrap'
import { useActiveOpenSignals } from '../../store/marketStore'
import { SignalCard } from './SignalCard'

export function SignalFeed() {
  useSignalsBootstrap()
  // useActiveOpenSignals derives a new array every call (filter+sort) for
  // whichever source is currently active — it already wraps useShallow
  // internally, so this component doesn't need to remember to.
  const openSignals = useActiveOpenSignals()

  if (openSignals.length === 0) {
    return (
      <p className="text-sm text-slate-400">
        No open signals right now — the pipeline only surfaces winning-caliber setups.
      </p>
    )
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {openSignals.map((signal) => (
        <SignalCard key={signal.id} signal={signal} />
      ))}
    </div>
  )
}
