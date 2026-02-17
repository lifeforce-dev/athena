import type { components } from '@/types/generated/api'

export type LedgerEntry = components['schemas']['LedgerEntry']
export type MonthSummary = components['schemas']['MonthSummary']
export type PayPeriodSummary = components['schemas']['PayPeriodSummary']
export type ProjectionResponse = components['schemas']['ProjectionResponse']

/** Ledger entry with money fields parsed to numbers for display. */
export interface ParsedLedgerEntry {
  date: string
  name: string
  delta: number
  balance: number
}

/** Month summary with money fields parsed to numbers for display. */
export interface ParsedMonthSummary {
  month: number
  year: number
  net: number
  balance: number
  is_partial: boolean
  covered_start: string
  covered_end: string
}

/** Pay period summary with money fields parsed to numbers for display. */
export interface ParsedPayPeriod {
  start_date: string
  end_date: string
  is_partial: boolean
  spent: number
  net: number
  start_balance: number
  end_balance: number
  min_balance: number
}
