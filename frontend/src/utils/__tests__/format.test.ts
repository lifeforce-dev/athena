/**
 * Tests for the currency-aware formatting layer.
 *
 * Validates that formatDollars, formatCents, formatSigned, and formatCurrency
 * correctly convert and format values based on the active CurrencyDisplay state.
 * These are the functions that every component calls -- if conversion is broken
 * here, every dollar amount in the app is wrong.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import {
  setCurrencyDisplay,
  formatDollars,
  formatCents,
  formatSigned,
  formatCurrency,
  toBaseCurrency,
  toDisplayCurrency,
  currencySymbol,
} from '@/utils/format'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setUsd() {
  setCurrencyDisplay({ code: 'USD', rate: 1 })
}

function setKrw(rate = 1350) {
  setCurrencyDisplay({ code: 'KRW', rate })
}

// ---------------------------------------------------------------------------
// formatDollars
// ---------------------------------------------------------------------------

describe('formatDollars', () => {
  beforeEach(setUsd)

  it('formats USD with dollar sign and commas', () => {
    expect(formatDollars(1234)).toBe('$1,234')
  })

  it('rounds to nearest dollar', () => {
    expect(formatDollars(1234.56)).toBe('$1,235')
    expect(formatDollars(1234.49)).toBe('$1,234')
  })

  it('uses absolute value (negative input)', () => {
    expect(formatDollars(-500)).toBe('$500')
  })

  it('handles zero', () => {
    expect(formatDollars(0)).toBe('$0')
  })

  it('converts to KRW with won sign', () => {
    setKrw(1350)
    expect(formatDollars(100)).toBe('\u20A9135,000')
  })

  it('rounds KRW to whole units', () => {
    setKrw(1345.5)
    // 100 * 1345.5 = 134,550
    expect(formatDollars(100)).toBe('\u20A9134,550')
  })

  it('handles large KRW amounts with proper grouping', () => {
    setKrw(1350)
    // 10000 * 1350 = 13,500,000
    expect(formatDollars(10000)).toBe('\u20A913,500,000')
  })

  it('reverts to USD after setCurrencyDisplay', () => {
    setKrw(1350)
    expect(formatDollars(100)).toBe('\u20A9135,000')

    setUsd()
    expect(formatDollars(100)).toBe('$100')
  })
})

// ---------------------------------------------------------------------------
// formatCents
// ---------------------------------------------------------------------------

describe('formatCents', () => {
  beforeEach(setUsd)

  it('formats USD with two decimal places', () => {
    expect(formatCents(1234.5)).toBe('$1,234.50')
  })

  it('uses absolute value', () => {
    expect(formatCents(-99.99)).toBe('$99.99')
  })

  it('preserves sub-dollar precision', () => {
    expect(formatCents(0.01)).toBe('$0.01')
  })

  it('KRW has no decimal places', () => {
    setKrw(1350)
    // 12.34 * 1350 = 16,659
    expect(formatCents(12.34)).toBe('\u20A916,659')
  })

  it('KRW rounds fractional won', () => {
    setKrw(1345.5)
    // 1 * 1345.5 = 1345.5 -> rounds to 1346
    expect(formatCents(1)).toBe('\u20A91,346')
  })
})

// ---------------------------------------------------------------------------
// formatSigned
// ---------------------------------------------------------------------------

describe('formatSigned', () => {
  beforeEach(setUsd)

  it('positive values get + prefix', () => {
    expect(formatSigned(500)).toBe('+$500')
  })

  it('negative values get - prefix', () => {
    expect(formatSigned(-500)).toBe('-$500')
  })

  it('zero gets + prefix', () => {
    expect(formatSigned(0)).toBe('+$0')
  })

  it('works with KRW conversion', () => {
    setKrw(1350)
    expect(formatSigned(100)).toBe('+\u20A9135,000')
    expect(formatSigned(-100)).toBe('-\u20A9135,000')
  })
})

// ---------------------------------------------------------------------------
// formatCurrency
// ---------------------------------------------------------------------------

describe('formatCurrency', () => {
  beforeEach(setUsd)

  it('formats USD as locale currency string', () => {
    const result = formatCurrency(1234.56)
    // toLocaleString('en-US', currency: 'USD') produces "$1,234.56"
    expect(result).toBe('$1,234.56')
  })

  it('converts to KRW with won sign and no decimals', () => {
    setKrw(1350)
    // 100 * 1350 = 135,000
    const result = formatCurrency(100)
    expect(result).toBe('\u20A9135,000')
  })
})

// ---------------------------------------------------------------------------
// Edge cases: rate boundaries
// ---------------------------------------------------------------------------

describe('rate edge cases', () => {
  it('rate of 1 means no conversion even for KRW display', () => {
    // This shouldn't happen in practice, but tests the boundary.
    setCurrencyDisplay({ code: 'KRW', rate: 1 })
    expect(formatDollars(100)).toBe('\u20A9100')
  })

  it('very small amounts survive KRW conversion', () => {
    setKrw(1350)
    // formatDollars rounds to nearest dollar first: round(0.5) = 1, then 1 * 1350 = 1,350
    expect(formatDollars(0.5)).toBe('\u20A91,350')
  })

  it('very large amounts survive KRW conversion', () => {
    setKrw(1350)
    // 1,000,000 * 1350 = 1,350,000,000
    expect(formatDollars(1000000)).toBe('\u20A91,350,000,000')
  })
})

// ---------------------------------------------------------------------------
// toDisplayCurrency / toBaseCurrency (round-trip conversion)
// ---------------------------------------------------------------------------

describe('toDisplayCurrency', () => {
  beforeEach(setUsd)

  it('returns same value when rate is 1 (USD)', () => {
    expect(toDisplayCurrency(100)).toBe(100)
  })

  it('multiplies by rate for KRW', () => {
    setKrw(1350)
    expect(toDisplayCurrency(100)).toBe(135_000)
  })

  it('handles zero', () => {
    setKrw(1350)
    expect(toDisplayCurrency(0)).toBe(0)
  })
})

describe('toBaseCurrency', () => {
  beforeEach(setUsd)

  it('returns same value when rate is 1 (USD)', () => {
    expect(toBaseCurrency(500)).toBe(500)
  })

  it('divides by rate for KRW', () => {
    setKrw(1350)
    expect(toBaseCurrency(135_000)).toBeCloseTo(100, 2)
  })

  it('handles fractional results', () => {
    setKrw(1350)
    // 5000 KRW / 1350 ~ 3.7037
    expect(toBaseCurrency(5000)).toBeCloseTo(3.7037, 3)
  })

  it('handles zero', () => {
    setKrw(1350)
    expect(toBaseCurrency(0)).toBe(0)
  })

  it('preserves negative sign', () => {
    setKrw(1350)
    expect(toBaseCurrency(-135_000)).toBeCloseTo(-100, 2)
  })
})

describe('round-trip conversion', () => {
  it('USD -> display -> base returns original value', () => {
    setKrw(1350)
    const original = 250.75
    const displayed = toDisplayCurrency(original)
    const restored = toBaseCurrency(displayed)
    expect(restored).toBeCloseTo(original, 10)
  })

  it('round-trip preserves sign for negative values', () => {
    setKrw(1350)
    const original = -1500
    const displayed = toDisplayCurrency(original)
    const restored = toBaseCurrency(displayed)
    expect(restored).toBeCloseTo(original, 10)
  })
})

// ---------------------------------------------------------------------------
// currencySymbol
// ---------------------------------------------------------------------------

describe('currencySymbol', () => {
  it('returns $ for USD', () => {
    setUsd()
    expect(currencySymbol()).toBe('$')
  })

  it('returns won sign for KRW', () => {
    setKrw()
    expect(currencySymbol()).toBe('\u20A9')
  })
})
