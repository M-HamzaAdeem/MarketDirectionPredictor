import { AppShell } from '../components/layout/AppShell'
import { PredictionPanel } from '../components/dashboard/PredictionPanel'
import { SignalFeed } from '../components/dashboard/SignalFeed'
import { SymbolCard } from '../components/dashboard/SymbolCard'
import { SymbolDetail } from '../components/dashboard/SymbolDetail'
import { usePricesBootstrap } from '../hooks/usePricesBootstrap'
import { ALL_SYMBOLS } from '../types/market'

export function DashboardPage() {
  usePricesBootstrap()

  return (
    <AppShell>
      <section>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {ALL_SYMBOLS.map((symbol) => (
            <SymbolCard key={symbol} symbol={symbol} />
          ))}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">Open Signals</h2>
        <SignalFeed />
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">Latest Predictions</h2>
        <PredictionPanel />
      </section>

      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">Symbol Detail</h2>
        <SymbolDetail />
      </section>
    </AppShell>
  )
}
