import { useState } from 'react'
import { useCandles } from '../../hooks/useCandles'
import { useSignalHistory } from '../../hooks/useSignalHistory'
import { useMarketStore } from '../../store/marketStore'
import type { MarketSymbol, Timeframe } from '../../types/market'
import { PerformanceStats } from './PerformanceStats'
import { PriceChart } from './PriceChart'
import { SignalHistoryTable } from './SignalHistoryTable'
import { SymbolTimeframeSelector } from './SymbolTimeframeSelector'

export function SymbolDetail() {
  const [symbol, setSymbol] = useState<MarketSymbol>('XAUUSD')
  const [timeframe, setTimeframe] = useState<Timeframe>('15m')

  const { data: candles = [] } = useCandles(symbol, timeframe)
  const { data: signalHistory = [] } = useSignalHistory(symbol)

  // .find() returns whatever object is currently in the map (or undefined)
  // — never a per-call-allocated container like selectOpenSignals' derived
  // .filter().sort() array — so useSyncExternalStore's Object.is check only
  // reports a change when the underlying signal object actually changed
  // (e.g. open -> resolved), which is a correct redraw, not a loop.
  const openSignal = useMarketStore((state) =>
    Object.values(state.signals).find(
      (signal) => signal.symbol === symbol && signal.entry_timeframe === timeframe && signal.status === 'open',
    ),
  )

  return (
    <div className="space-y-6">
      <SymbolTimeframeSelector
        symbol={symbol}
        timeframe={timeframe}
        onSymbolChange={setSymbol}
        onTimeframeChange={setTimeframe}
      />

      <PriceChart symbol={symbol} timeframe={timeframe} candles={candles} signal={openSignal} />

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">Performance</h3>
        <PerformanceStats signals={signalHistory} />
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">Signal History</h3>
        <SignalHistoryTable signals={signalHistory} />
      </div>
    </div>
  )
}
