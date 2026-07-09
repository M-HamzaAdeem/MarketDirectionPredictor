import { useActivePrices } from '../../store/marketStore'
import type { MarketSymbol } from '../../types/market'

interface SymbolCardProps {
  symbol: MarketSymbol
}

export function SymbolCard({ symbol }: SymbolCardProps) {
  const price = useActivePrices()[symbol]

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="text-sm text-slate-400">{symbol}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-100">
        {price ? price.price.toLocaleString(undefined, { maximumFractionDigits: 5 }) : '—'}
      </div>
    </div>
  )
}
