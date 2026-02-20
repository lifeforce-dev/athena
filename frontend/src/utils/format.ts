// -- Currency display state (pushed in by the currency store) ----------------
// Uses a Vue shallowRef so that template expressions calling formatDollars()
// or formatCents() automatically re-render when the display currency changes.

import { shallowRef } from 'vue'

export interface CurrencyDisplay {
  code: 'USD' | 'KRW'
  rate: number  // 1.0 for base currency, exchange rate otherwise
}

const _cd = shallowRef<CurrencyDisplay>({ code: 'USD', rate: 1 })

/** Called by the currency store whenever display currency or rate changes. */
export function setCurrencyDisplay(cd: CurrencyDisplay): void {
  _cd.value = cd
}

function convert(value: number): number {
  const cd = _cd.value
  return cd.rate === 1 ? value : value * cd.rate
}

function prefix(): string {
  return _cd.value.code === 'KRW' ? '\u20A9' : '$'
}

// -- Money formatting (reads current display currency implicitly) ------------

export const formatCurrency = (value: number): string => {
  const converted = convert(value)
  if (_cd.value.code === 'KRW') {
    return prefix() + Math.round(Math.abs(converted)).toLocaleString()
  }
  return converted.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 })
}

export const formatSigned = (value: number): string => {
  const sign = value >= 0 ? '+' : '-'
  return `${sign}${formatDollars(Math.abs(value))}`
}

/** Rounded whole-unit display: "$1,234" or "\u20A91,650,000". */
export const formatDollars = (value: number): string => {
  const converted = convert(Math.abs(Math.round(value)))
  return prefix() + Math.round(converted).toLocaleString()
}

/** Two-decimal display: "$1,234.56". KRW rounds to whole units. */
export const formatCents = (value: number): string => {
  const converted = convert(Math.abs(value))
  if (_cd.value.code === 'KRW') {
    return prefix() + Math.round(converted).toLocaleString()
  }
  return prefix() + converted.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/** Short date display: "Feb 17". */
export const shortDate = (dateStr: string): string =>
  parseLocalDate(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

/** Calendar days between two YYYY-MM-DD strings. */
export const daysBetween = (startDate: string, endDate: string): number =>
  Math.round((parseLocalDate(endDate).getTime() - parseLocalDate(startDate).getTime()) / 864e5)

/**
 * Parse a Decimal string from the API into a number for display.
 * The backend serializes Decimal as JSON strings to avoid IEEE 754 loss.
 * Returns 0 for unparseable values rather than propagating NaN.
 */
export const parseMoney = (value: string): number => {
  const parsed = Number(value)
  return Number.isNaN(parsed) ? 0 : parsed
}

/**
 * Format a Date as a local YYYY-MM-DD string without UTC conversion.
 * Avoids the timezone off-by-one bug from Date.toISOString().slice(0, 10).
 */
export const toLocalDateString = (date: Date): string => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * Parse a YYYY-MM-DD string as a local date (not UTC).
 * Using new Date('YYYY-MM-DD') interprets it as UTC midnight, which shifts
 * the displayed day by -1 for users west of UTC.
 */
export const parseLocalDate = (dateStr: string): Date => {
  const [year, month, day] = dateStr.split('-').map(Number)
  return new Date(year, month - 1, day)
}
