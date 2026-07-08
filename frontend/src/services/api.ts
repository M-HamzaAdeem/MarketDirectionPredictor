import { apiGet } from './apiClient'
import type { Config } from '../types/config'
import type { Candle, MarketSymbol, Price, Timeframe } from '../types/market'
import type { Prediction } from '../types/prediction'
import type { Signal } from '../types/signal'

export function getSymbols(): Promise<MarketSymbol[]> {
  return apiGet<MarketSymbol[]>('/symbols')
}

/** Latest price per configured symbol — the live tick cache, falling back
 * server-side to the latest closed 1m candle for a symbol that hasn't
 * ticked yet this session. Omits a symbol with neither. */
export function getPrices(): Promise<Price[]> {
  return apiGet<Price[]>('/prices')
}

export function getConfig(): Promise<Config> {
  return apiGet<Config>('/config')
}

export function getCandles(symbol: MarketSymbol, timeframe: Timeframe, limit = 100): Promise<Candle[]> {
  return apiGet<Candle[]>(`/candles/${symbol}/${timeframe}?limit=${limit}`)
}

export function getOpenSignals(symbol?: MarketSymbol): Promise<Signal[]> {
  const query = symbol ? `?symbol=${symbol}` : ''
  return apiGet<Signal[]>(`/signals/open${query}`)
}

export function getSignalHistory(symbol: MarketSymbol, limit = 100): Promise<Signal[]> {
  return apiGet<Signal[]>(`/signals/${symbol}/history?limit=${limit}`)
}

/** Computes a prediction on demand from whatever closed candles already
 * exist — no live candle-close event required. 404s if there isn't at
 * least one closed candle yet for this symbol/timeframe. */
export function getPredictionLatest(symbol: MarketSymbol, timeframe: Timeframe): Promise<Prediction> {
  return apiGet<Prediction>(`/predictions/${symbol}/${timeframe}/latest`)
}
