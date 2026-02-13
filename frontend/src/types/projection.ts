/**
 * Projection API response types.
 *
 * These are manually maintained to match the Pydantic schemas in app/models/schemas.py.
 * To regenerate from the OpenAPI spec instead:
 *   1. Start the API server: uvicorn app.main:app
 *   2. Run: npm run generate:types
 *   3. Replace these with re-exports from '@/types/generated/api'
 */

export interface LedgerEntry {
  date: string
  name: string
  delta: number
  balance: number
}

export interface MonthSummary {
  month: number
  year: number
  net: number
  balance: number
  is_partial: boolean
  covered_start: string
  covered_end: string
}

export interface PayPeriodSummary {
  start_date: string
  end_date: string
  is_partial: boolean
  spent: number
  net: number
  start_balance: number
  end_balance: number
  min_balance: number
}

export interface ProjectionResponse {
  as_of: string
  from_date: string
  current_balance: number
  ledger: LedgerEntry[]
  months: MonthSummary[]
  pay_periods: PayPeriodSummary[]
}
