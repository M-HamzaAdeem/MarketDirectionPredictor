import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useMarketStore } from '../store/marketStore'
import type { WebSocketMessage } from '../types/websocket'
import { candlesKey } from './useCandles'
import { signalHistoryKey } from './useSignalHistory'

const WS_URL: string = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000/ws'
const INITIAL_RECONNECT_DELAY_MS = 1000
const MAX_RECONNECT_DELAY_MS = 30000
const RECONNECT_BACKOFF_MULTIPLIER = 2

/** Connects to the backend's broadcast-only /ws endpoint and dispatches
 * every message into the market store. Reconnects with exponential backoff
 * (capped, reset on a successful connection) if the connection drops. */
export function useMarketSocket(): void {
  const setFeedStatus = useMarketStore((state) => state.setFeedStatus)
  const setPrice = useMarketStore((state) => state.setPrice)
  const setPrediction = useMarketStore((state) => state.setPrediction)
  const upsertSignal = useMarketStore((state) => state.upsertSignal)
  const queryClient = useQueryClient()

  useEffect(() => {
    let socket: WebSocket | null = null
    let reconnectTimer: number | undefined
    let reconnectDelay = INITIAL_RECONNECT_DELAY_MS
    let cancelled = false

    function handleMessage(event: MessageEvent<string>): void {
      let message: WebSocketMessage
      try {
        message = JSON.parse(event.data) as WebSocketMessage
      } catch {
        return // malformed frame: drop it, don't let it tear down the connection
      }

      switch (message.type) {
        case 'feed_status':
          setFeedStatus(message.status, message.timestamp)
          break
        case 'price':
          setPrice({ symbol: message.symbol, price: message.price, timestamp: message.timestamp })
          break
        case 'prediction':
          setPrediction(message)
          // A prediction is only ever broadcast when its symbol/timeframe's
          // candle just closed (PredictionService reacts to every close,
          // not just some), so this is the precise signal that the Symbol
          // Detail chart's candle list is now stale — unlike price ticks,
          // which fire far too often to invalidate on. Partial queryKey
          // match invalidates every `limit` variant already fetched.
          void queryClient.invalidateQueries({ queryKey: candlesKey(message.symbol, message.timeframe) })
          break
        case 'signal':
          upsertSignal(message)
          // Same reasoning: a signal message means this symbol's history
          // just changed (opened or resolved), so its history table is stale.
          void queryClient.invalidateQueries({ queryKey: signalHistoryKey(message.symbol) })
          break
      }
    }

    function detach(target: WebSocket): void {
      target.onopen = null
      target.onmessage = null
      target.onclose = null
      target.onerror = null
    }

    function connect(): void {
      socket = new WebSocket(WS_URL)
      socket.onopen = () => {
        reconnectDelay = INITIAL_RECONNECT_DELAY_MS
      }
      socket.onmessage = handleMessage
      socket.onerror = () => {
        // The browser follows this with onclose, which schedules the
        // reconnect — this handler only makes the disconnected state
        // visible instead of only appearing in the console.
        setFeedStatus('disconnected', new Date().toISOString())
      }
      socket.onclose = () => {
        if (!cancelled) {
          reconnectTimer = window.setTimeout(connect, reconnectDelay)
          reconnectDelay = Math.min(reconnectDelay * RECONNECT_BACKOFF_MULTIPLIER, MAX_RECONNECT_DELAY_MS)
        }
      }
    }

    connect()

    return () => {
      cancelled = true
      window.clearTimeout(reconnectTimer)
      if (socket) {
        detach(socket)
        socket.close()
      }
    }
  }, [setFeedStatus, setPrice, setPrediction, upsertSignal, queryClient])
}
