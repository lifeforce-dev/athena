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
      has_initial_balance: boolean
      ledger: components['schemas']['LedgerEntry'][]
      months: components['schemas']['MonthSummary'][]
      pay_periods: components['schemas']['PayPeriodSummary'][]
    }
    CommitmentResponse: {
      id: number
      name: string
      amount: string
      frequency: string
      day_of_month: number | null
      anchor_date: string | null
      one_time_date: string | null
      start_date: string
      end_date: string | null
      is_paycheck: boolean
      is_active: boolean
      created_at: string
      updated_at: string
    }
    CommitmentCreate: {
      name: string
      amount: string
      frequency: 'daily' | 'weekly' | 'biweekly' | 'monthly' | 'once'
      day_of_month?: number | null
      anchor_date?: string | null
      one_time_date?: string | null
      start_date: string
      end_date?: string | null
      is_paycheck?: boolean
    }
    CommitmentUpdate: {
      name?: string | null
      amount?: string | null
      frequency?: 'daily' | 'weekly' | 'biweekly' | 'monthly' | 'once' | null
      day_of_month?: number | null
      anchor_date?: string | null
      one_time_date?: string | null
      start_date?: string | null
      end_date?: string | null
      is_paycheck?: boolean | null
    }
    BalanceSnapshotResponse: {
      id: number
      balance: string
      account_label: string | null
      observed_at: string
      source: string
      created_at: string
    }
    ManualBalanceCreate: {
      balance: string
      observed_at: string
      account_label?: string | null
    }
    TransactionResponse: {
      id: number
      amount: string
      merchant: string | null
      card_last_four: string | null
      purchase_date: string
      created_at: string
    }
    UserResponse: {
      id: number
      discord_id: string
      username: string
    }
  }
}
