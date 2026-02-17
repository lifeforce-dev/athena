import { computed, ref } from 'vue'
import type { ProjectionResponse, ParsedLedgerEntry, ParsedPayPeriod } from '@/types/projection'
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

  const ledger = computed<ParsedLedgerEntry[]>(() =>
    (data.value?.ledger ?? []).map((entry) => ({
      date: entry.date,
      name: entry.name,
      delta: parseMoney(entry.delta),
      balance: parseMoney(entry.balance),
    }))
  )

  const payPeriods = computed<ParsedPayPeriod[]>(() =>
    (data.value?.pay_periods ?? []).map((pp) => ({
      start_date: pp.start_date,
      end_date: pp.end_date,
      is_partial: pp.is_partial,
      spent: parseMoney(pp.spent),
      net: parseMoney(pp.net),
      start_balance: parseMoney(pp.start_balance),
      end_balance: parseMoney(pp.end_balance),
      min_balance: parseMoney(pp.min_balance),
    }))
  )

  return { data, loading, error, load, currentBalance, payPeriods, ledger }
}
