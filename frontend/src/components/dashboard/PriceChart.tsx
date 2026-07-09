import {
  CandlestickSeries,
  createChart,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import type { Candle, MarketSymbol, Timeframe } from '../../types/market'
import type { Signal } from '../../types/signal'
import { describeChart } from '../../utils/describeChart'
import { pricePrecision } from '../../utils/priceFormat'

const CHART_HEIGHT_PX = 480

// Candle timestamps are stored/served in UTC, but the trader watching this
// chart is in UTC+5 — shifting the timestamp itself (rather than relying on
// the viewer's browser timezone) means the axis always reads correctly
// regardless of what machine it's viewed from.
const DISPLAY_UTC_OFFSET_HOURS = 5
const DISPLAY_UTC_OFFSET_SECONDS = DISPLAY_UTC_OFFSET_HOURS * 3600

function toDisplayTime(isoString: string): UTCTimestamp {
  return (Math.floor(new Date(isoString).getTime() / 1000) + DISPLAY_UTC_OFFSET_SECONDS) as UTCTimestamp
}

// Renders as e.g. "Jul 8, 14:30" using UTC getters — since the timestamp
// already has DISPLAY_UTC_OFFSET_SECONDS baked in, reading it back with UTC
// getters yields the shifted (local) calendar time regardless of the
// viewer's own browser timezone.
function formatDisplayTime(time: Time): string {
  // Intraday series (1m/5m/15m/1h/4h, always time-visible) always hand back
  // the numeric UTCTimestamp form, never the day-granular BusinessDay
  // object — but the type allows both, so guard rather than cast blindly.
  if (typeof time !== 'number') return ''

  const date = new Date(time * 1000)
  const datePart = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
  const timePart = date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'UTC',
  })
  return `${datePart}, ${timePart}`
}

interface PriceChartProps {
  symbol: MarketSymbol
  timeframe: Timeframe
  candles: Candle[]
  /** The open signal for this symbol/timeframe, if any — drawn as entry/stop/target lines. */
  signal?: Signal | null
}

export function PriceChart({ symbol, timeframe, candles, signal }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const chart: IChartApi = createChart(container, {
      layout: { background: { color: 'transparent' }, textColor: '#94a3b8' },
      grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
      width: container.clientWidth,
      height: CHART_HEIGHT_PX,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        tickMarkFormatter: formatDisplayTime,
      },
      localization: {
        timeFormatter: formatDisplayTime,
      },
    })
    chartRef.current = chart

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
      chartRef.current = null
      seriesRef.current = null
    }
  }, [])

  useEffect(() => {
    const series = seriesRef.current
    if (!series) return

    const precision = pricePrecision(symbol)
    series.applyOptions({
      priceFormat: { type: 'price', precision, minMove: 10 ** -precision },
    })
  }, [symbol])

  useEffect(() => {
    const chart = chartRef.current
    const series = seriesRef.current
    if (!chart || !series) return

    series.setData(
      candles.map((candle) => ({
        time: toDisplayTime(candle.open_time),
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      })),
    )
    // setData() alone doesn't reset the visible time range — without this,
    // switching symbol/timeframe keeps whatever window was visible for the
    // previous data, which can make an entirely different price range
    // (e.g. XAUUSD's ~4000s vs EURUSD's ~1.1s) look like it never rescaled.
    chart.timeScale().fitContent()
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

  return <div ref={containerRef} className="w-full" role="img" aria-label={describeChart(symbol, timeframe, candles)} />
}
