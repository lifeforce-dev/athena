import { computed, ref } from 'vue'
import type { ProjectionResponse } from '@/types/projection'
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
  const payPeriods = computed(() => data.value?.pay_periods ?? [])
  const ledger = computed(() => data.value?.ledger ?? [])

  return { data, loading, error, load, currentBalance, payPeriods, ledger }
}
