// -- Currency display state (pushed in by the currency store) ----------------
// Uses a Vue shallowRef so that template expressions calling formatDollars()
// or formatCents() automatically re-render when the display currency changes.

import { shallowRef } from 'vue'
import { getCurrencyConfig } from '@/config/currencies'

export interface CurrencyDisplay {
  code: string
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
  return getCurrencyConfig(_cd.value.code).symbol
}

function decimals(): number {
  return getCurrencyConfig(_cd.value.code).decimals
}

/** Convert a base-currency amount to the active display currency. */
export function toDisplayCurrency(value: number): number {
  return convert(value)
}

/** Convert a display-currency amount back to base currency for storage. */
export function toBaseCurrency(displayAmount: number): number {
  const cd = _cd.value
  return cd.rate === 1 ? displayAmount : displayAmount / cd.rate
}

/** The symbol for the active display currency. */
export function currencySymbol(): string {
  return prefix()
}

// -- Money formatting (reads current display currency implicitly) ------------

export const formatCurrency = (value: number): string => {
  const converted = convert(value)
  const dec = decimals()

  if (dec === 0) {
    return prefix() + Math.round(Math.abs(converted)).toLocaleString()
  }

  return converted.toLocaleString('en-US', {
    style: 'currency',
    currency: _cd.value.code,
    maximumFractionDigits: dec,
  })
}

export const formatSigned = (value: number): string => {
  const sign = value >= 0 ? '+' : '-'
  return `${sign}${formatDollars(Math.abs(value))}`
}

/** Rounded whole-unit display: "$1,234" or "Won1,650,000". */
export const formatDollars = (value: number): string => {
  const converted = convert(Math.abs(Math.round(value)))
  return prefix() + Math.round(converted).toLocaleString()
}

/** Decimal display: "$1,234.56". Zero-decimal currencies round to whole units. */
export const formatCents = (value: number): string => {
  const converted = convert(Math.abs(value))
  const dec = decimals()

  if (dec === 0) {
    return prefix() + Math.round(converted).toLocaleString()
  }

  return prefix() + converted.toLocaleString(undefined, { minimumFractionDigits: dec, maximumFractionDigits: dec })
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
