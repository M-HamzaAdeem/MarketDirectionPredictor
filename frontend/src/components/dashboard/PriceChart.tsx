import {
  CandlestickSeries,
  createChart,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type UTCTimestamp,
} from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import type { Candle } from '../../types/market'
import type { Signal } from '../../types/signal'

const CHART_HEIGHT_PX = 320

interface PriceChartProps {
  candles: Candle[]
  /** The open signal for this symbol/timeframe, if any — drawn as entry/stop/target lines. */
  signal?: Signal | null
}

export function PriceChart({ candles, signal }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const chart: IChartApi = createChart(container, {
      layout: { background: { color: 'transparent' }, textColor: '#94a3b8' },
      grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
      width: container.clientWidth,
      height: CHART_HEIGHT_PX,
    })

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#34d399',
      downColor: '#f87171',
      borderVisible: false,
      wickUpColor: '#34d399',
      wickDownColor: '#f87171',
    })
    seriesRef.current = series

    // A window resize listener alone misses the container resizing without
    // the window changing (e.g. a sidebar collapsing) — the container is
    // w-full, so this is a real case, not a hypothetical one.
    const resizeObserver = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width
      if (width !== undefined) {
        chart.applyOptions({ width })
      }
    })
    resizeObserver.observe(container)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
      seriesRef.current = null
    }
  }, [])

  useEffect(() => {
    const series = seriesRef.current
    if (!series) return

    series.setData(
      candles.map((candle) => ({
        time: Math.floor(new Date(candle.open_time).getTime() / 1000) as UTCTimestamp,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      })),
    )
  }, [candles])

  useEffect(() => {
    const series = seriesRef.current
    if (!series || !signal) return

    // lightweight-charts has no "clear all price lines" call — track and
    // remove exactly the ones this effect created.
    const lines: IPriceLine[] = [
      series.createPriceLine({ price: signal.entry, color: '#60a5fa', lineWidth: 1, title: 'Entry' }),
      series.createPriceLine({ price: signal.stop, color: '#f87171', lineWidth: 1, title: 'Stop' }),
      series.createPriceLine({ price: signal.target, color: '#34d399', lineWidth: 1, title: 'Target' }),
    ]

    return () => {
      for (const line of lines) {
        series.removePriceLine(line)
      }
    }
  }, [signal])

  return <div ref={containerRef} className="w-full" />
}
