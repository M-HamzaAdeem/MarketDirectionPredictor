import { DisclaimerBanner } from '../components/dashboard/DisclaimerBanner'
import { FeedStatusIndicator } from '../components/dashboard/FeedStatusIndicator'
import { PredictionPanel } from '../components/dashboard/PredictionPanel'
import { SignalFeed } from '../components/dashboard/SignalFeed'
import { SymbolCard } from '../components/dashboard/SymbolCard'
import { SymbolDetail } from '../components/dashboard/SymbolDetail'
import { useMarketSocket } from '../hooks/useMarketSocket'
import type { MarketSymbol } from '../types/market'

const SYMBOLS: MarketSymbol[] = ['XAUUSD', 'EURUSD', 'AUDUSD']

export function DashboardPage() {
  useMarketSocket()

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <DisclaimerBanner />

      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
        <h1 className="text-lg font-semibold">Market Direction Predictor</h1>
        <FeedStatusIndicator />
      </header>

      <main className="flex-1 space-y-8 px-6 py-6">
        <section>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {SYMBOLS.map((symbol) => (
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
      </main>
    </div>
  )
}
