/**
 * This file is generated from the FastAPI OpenAPI schema.
 * Regenerate with: npm run generate:types
 */

export interface components {
  schemas: {
    LedgerEntry: {
      date: string
      name: string
      delta: number
      balance: number
    }
    MonthSummary: {
      month: number
      year: number
      net: number
      balance: number
      is_partial: boolean
      covered_start: string
      covered_end: string
    }
    PayPeriodSummary: {
      start_date: string
      end_date: string
      is_partial: boolean
      spent: number
      net: number
      start_balance: number
      end_balance: number
      min_balance: number
    }
    ProjectionResponse: {
      as_of: string
      from_date: string
      current_balance: number
      ledger: components['schemas']['LedgerEntry'][]
      months: components['schemas']['MonthSummary'][]
      pay_periods: components['schemas']['PayPeriodSummary'][]
    }
  }
}
