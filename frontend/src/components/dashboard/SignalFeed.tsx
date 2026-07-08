import { useShallow } from 'zustand/react/shallow'
import { useSignalsBootstrap } from '../../hooks/useSignalsBootstrap'
import { selectOpenSignals, useMarketStore } from '../../store/marketStore'
import { SignalCard } from './SignalCard'

export function SignalFeed() {
  useSignalsBootstrap()
  // selectOpenSignals derives a new array every call (filter+sort); useShallow
  // compares its elements instead of the array reference, so the component
  // only re-renders when the actual open-signal set changes — without this,
  // useSyncExternalStore sees a "new" snapshot every render and loops.
  const openSignals = useMarketStore(useShallow(selectOpenSignals))

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
