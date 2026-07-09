import { apiGet } from './apiClient'
import type { Config } from '../types/config'
import type { Candle, DataSource, MarketSymbol, Price, Timeframe } from '../types/market'
import type { Prediction } from '../types/prediction'
import type { Signal } from '../types/signal'

const DEFAULT_SOURCE: DataSource = 'twelve_data'

export function getSymbols(): Promise<MarketSymbol[]> {
  return apiGet<MarketSymbol[]>('/symbols')
}

/** Latest price per configured symbol for one source — the live tick
 * cache, falling back server-side to the latest closed 1m candle for a
 * symbol that hasn't ticked yet this session. Omits a symbol with neither. */
export function getPrices(source: DataSource = DEFAULT_SOURCE): Promise<Price[]> {
  return apiGet<Price[]>(`/prices?source=${source}`)
}

export function getConfig(): Promise<Config> {
  return apiGet<Config>('/config')
}

export function getCandles(
  symbol: MarketSymbol,
  timeframe: Timeframe,
  source: DataSource = DEFAULT_SOURCE,
  limit = 100,
): Promise<Candle[]> {
  return apiGet<Candle[]>(`/candles/${symbol}/${timeframe}?limit=${limit}&source=${source}`)
}

export function getSignalHistory(
  symbol: MarketSymbol,
  source: DataSource = DEFAULT_SOURCE,
  limit = 100,
): Promise<Signal[]> {
  return apiGet<Signal[]>(`/signals/${symbol}/history?limit=${limit}&source=${source}`)
}

/** Returns the already-open signal for this symbol as-is if one exists;
 * otherwise computes one on demand from whatever closed candles already
 * exist — no live 15m candle-close event required. 404s if neither an
 * open signal nor a winning-caliber setup exists right now. */
export function getSignalLatest(symbol: MarketSymbol, source: DataSource = DEFAULT_SOURCE): Promise<Signal> {
  return apiGet<Signal>(`/signals/${symbol}/latest?source=${source}`)
}

/** Computes a prediction on demand from whatever closed candles already
 * exist — no live candle-close event required. 404s if there isn't at
 * least one closed candle yet for this symbol/timeframe. */
export function getPredictionLatest(
  symbol: MarketSymbol,
  timeframe: Timeframe,
  source: DataSource = DEFAULT_SOURCE,
): Promise<Prediction> {
  return apiGet<Prediction>(`/predictions/${symbol}/${timeframe}/latest?source=${source}`)
}
