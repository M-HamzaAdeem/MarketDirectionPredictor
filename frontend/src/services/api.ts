import { apiGet } from './apiClient'
import type { Config } from '../types/config'
import type { Candle, MarketSymbol, Timeframe } from '../types/market'
import type { Prediction } from '../types/prediction'
import type { Signal } from '../types/signal'

export function getSymbols(): Promise<MarketSymbol[]> {
  return apiGet<MarketSymbol[]>('/symbols')
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

export function getPredictionHistory(symbol: MarketSymbol, timeframe: Timeframe, limit = 100): Promise<Prediction[]> {
  return apiGet<Prediction[]>(`/predictions/${symbol}/${timeframe}/history?limit=${limit}`)
}
