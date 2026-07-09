import type { Candle, MarketSymbol, Timeframe } from '../types/market'
import { pricePrecision } from './priceFormat'

/** Text summary of a candlestick chart's current content, for the chart
 * container's aria-label — the chart itself is a canvas lightweight-charts
 * draws into, opaque to screen readers with no text content of its own. */
export function describeChart(symbol: MarketSymbol, timeframe: Timeframe, candles: Candle[]): string {
  if (candles.length === 0) return `Candlestick chart for ${symbol} ${timeframe}, no candles loaded yet`

  const latestClose = candles[candles.length - 1].close
  const candleWord = candles.length === 1 ? 'candle' : 'candles'
  return `Candlestick chart for ${symbol} ${timeframe}, ${candles.length} ${candleWord}, current price ${latestClose.toFixed(pricePrecision(symbol))}`
}
