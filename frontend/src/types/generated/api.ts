/**
 * This file is generated from the FastAPI OpenAPI schema.
 * Regenerate with: npm run generate:types
 */

export interface components {
  schemas: {
    LedgerEntry: {
      date: string
      name: string
      delta: string
      balance: string
    }
    MonthSummary: {
      month: number
      year: number
      net: string
      balance: string
      is_partial: boolean
      covered_start: string
      covered_end: string
    }
    PayPeriodSummary: {
      start_date: string
      end_date: string
      is_partial: boolean
      spent: string
      net: string
      start_balance: string
      end_balance: string
      min_balance: string
    }
    ProjectionResponse: {
      as_of: string
      from_date: string
      current_balance: string
      ledger: components['schemas']['LedgerEntry'][]
      months: components['schemas']['MonthSummary'][]
      pay_periods: components['schemas']['PayPeriodSummary'][]
    }
  }
}
