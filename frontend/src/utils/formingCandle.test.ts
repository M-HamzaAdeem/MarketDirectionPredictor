import { describe, expect, it } from 'vitest'
import { bucketStart, formingCandleIsStale, updateFormingCandle } from './formingCandle'

describe('bucketStart', () => {
  it('floors a 15m timestamp to the start of its bucket', () => {
    expect(bucketStart('2026-01-01T10:07:30Z', '15m')).toBe('2026-01-01T10:00:00.000Z')
    expect(bucketStart('2026-01-01T10:14:59Z', '15m')).toBe('2026-01-01T10:00:00.000Z')
    expect(bucketStart('2026-01-01T10:15:00Z', '15m')).toBe('2026-01-01T10:15:00.000Z')
  })

  it('floors a 1h timestamp to the start of its bucket', () => {
    expect(bucketStart('2026-01-01T10:59:59Z', '1h')).toBe('2026-01-01T10:00:00.000Z')
    expect(bucketStart('2026-01-01T11:00:00Z', '1h')).toBe('2026-01-01T11:00:00.000Z')
  })

  it('floors a 1d timestamp to a UTC midnight boundary', () => {
    expect(bucketStart('2026-01-01T13:45:00Z', '1d')).toBe('2026-01-01T00:00:00.000Z')
  })

  it('floors a 1w timestamp to a Thursday boundary, matching the backend epoch-floor convention', () => {
    // Mirrors backend test_bucket_start_weekly_is_thursday_anchored_not_monday
    // in tests/unit/test_time.py -- 2026-01-01 is itself a Thursday.
    expect(bucketStart('2026-01-01T13:45:00Z', '1w')).toBe('2026-01-01T00:00:00.000Z')
  })
})

describe('updateFormingCandle', () => {
  it('starts a fresh bar from the first tick when there is no previous state', () => {
    const result = updateFormingCandle(null, 100.0, '2026-01-01T10:05:00Z', '15m')
    expect(result).toEqual({ open_time: '2026-01-01T10:00:00.000Z', open: 100.0, high: 100.0, low: 100.0, close: 100.0 })
  })

  it('extends high/low and updates close for a tick within the same bucket', () => {
    const first = updateFormingCandle(null, 100.0, '2026-01-01T10:05:00Z', '15m')
    const second = updateFormingCandle(first, 102.0, '2026-01-01T10:08:00Z', '15m')
    const third = updateFormingCandle(second, 98.0, '2026-01-01T10:10:00Z', '15m')

    expect(third).toEqual({ open_time: '2026-01-01T10:00:00.000Z', open: 100.0, high: 102.0, low: 98.0, close: 98.0 })
  })

  it('starts a new bar once a tick lands in the next bucket, discarding the old one', () => {
    const first = updateFormingCandle(null, 100.0, '2026-01-01T10:14:00Z', '15m')
    const rolledOver = updateFormingCandle(first, 105.0, '2026-01-01T10:15:30Z', '15m')

    expect(rolledOver).toEqual({
      open_time: '2026-01-01T10:15:00.000Z',
      open: 105.0,
      high: 105.0,
      low: 105.0,
      close: 105.0,
    })
  })
})

describe('formingCandleIsStale', () => {
  it('is never stale when no closed candle exists yet', () => {
    expect(formingCandleIsStale('2026-01-01T10:15:00.000Z', null)).toBe(false)
  })

  it('is stale when the forming bucket is at or before the last closed one', () => {
    expect(formingCandleIsStale('2026-01-01T10:00:00.000Z', '2026-01-01T10:15:00.000Z')).toBe(true)
    expect(formingCandleIsStale('2026-01-01T10:15:00.000Z', '2026-01-01T10:15:00.000Z')).toBe(true)
  })

  it('is not stale when the forming bucket is strictly after the last closed one', () => {
    expect(formingCandleIsStale('2026-01-01T10:30:00.000Z', '2026-01-01T10:15:00.000Z')).toBe(false)
  })

  it('agrees with the backend wire format (no millisecond suffix) despite bucketStart() always emitting one', () => {
    // Confirmed real backend format for a whole-second candle timestamp
    // (see Pydantic's model_dump_json output): "...T10:15:00Z", no ".000".
    // bucketStart()'s toISOString() always includes it. Equal instants
    // must compare as stale (already confirmed closed) regardless.
    expect(formingCandleIsStale('2026-01-01T10:15:00.000Z', '2026-01-01T10:15:00Z')).toBe(true)
    expect(formingCandleIsStale('2026-01-01T10:30:00.000Z', '2026-01-01T10:15:00Z')).toBe(false)
  })

  it('is robust to a differing UTC offset notation, unlike a plain string comparison would be', () => {
    // A "+00:00" offset (an equally valid ISO 8601 rendering of UTC) sorts
    // *after* "." lexicographically -- a naive string comparison of these
    // two equal instants would incorrectly conclude the forming candle is
    // newer (not stale) and let a confirmed-closed bucket keep being
    // redrawn. Comparing epoch instants sidesteps this regardless of
    // which valid UTC notation either side happens to use.
    expect(formingCandleIsStale('2026-01-01T10:15:00.000Z', '2026-01-01T10:15:00+00:00')).toBe(true)
  })
})
