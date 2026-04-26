import { computed, ref } from 'vue'
import type { ProjectionResponse, ParsedLedgerEntry, ParsedPayPeriod, ParsedRiskAnalysis } from '@/types/projection'
import { fetchProjection } from '@/api/projection'
import { parseMoney } from '@/utils/format'

export function useProjection() {
  const data = ref<ProjectionResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(asOf: string, fromDate?: string) {
    loading.value = true
    error.value = null
    try {
      data.value = await fetchProjection(asOf, fromDate)
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    } finally {
      loading.value = false
    }
  }

  const currentBalance = computed(() => parseMoney(data.value?.current_balance ?? '0'))

  const hasInitialBalance = computed(() => data.value?.has_initial_balance ?? false)

  const ledger = computed<ParsedLedgerEntry[]>(() =>
    (data.value?.ledger ?? []).map((entry) => ({
      date: entry.date,
      name: entry.name,
      delta: parseMoney(entry.delta),
      balance: parseMoney(entry.balance),
    }))
  )

  const payPeriods = computed<ParsedPayPeriod[]>(() =>
    (data.value?.pay_periods ?? []).map((period) => ({
      start_date: period.start_date,
      end_date: period.end_date,
      is_partial: period.is_partial,
      spent: parseMoney(period.spent),
      net: parseMoney(period.net),
      start_balance: parseMoney(period.start_balance),
      end_balance: parseMoney(period.end_balance),
      min_balance: parseMoney(period.min_balance),
    }))
  )

  /** Risk analysis fields computed by the backend (expenses-before-income walk). */
  const riskAnalysis = computed<ParsedRiskAnalysis>(() => ({
    lowestBalance: parseMoney(data.value?.lowest_balance ?? '0'),
    lowestDate: data.value?.lowest_date ?? null,
    riskLevel: data.value?.risk_level ?? 'comfortable',
    totalOutflows: parseMoney(data.value?.total_outflows ?? '0'),
    totalInflows: parseMoney(data.value?.total_inflows ?? '0'),
    goesNegative: data.value?.goes_negative ?? false,
    negativeDate: data.value?.negative_date ?? null,
    negativeBalance: data.value?.negative_balance != null ? parseMoney(data.value.negative_balance) : null,
    daysUntilNegative: data.value?.days_until_negative ?? null,
    drainRate: parseMoney(data.value?.drain_rate ?? '0'),
    lowestRatio: parseMoney(data.value?.lowest_ratio ?? '1'),
  }))

  return { data, loading, error, load, currentBalance, hasInitialBalance, payPeriods, ledger, riskAnalysis }
}
