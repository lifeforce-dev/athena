import { ref, computed, onMounted } from 'vue'
import type { CommitmentResponse, CommitmentCreate, CommitmentUpdate, Frequency } from '@/types/commitment'
import {
  fetchCommitments,
  createCommitment as apiCreate,
  updateCommitment as apiUpdate,
  deleteCommitment as apiDelete,
} from '@/api/commitments'
import { parseMoney } from '@/utils/format'

export function useCommitments() {
  const commitments = ref<CommitmentResponse[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      commitments.value = await fetchCommitments()
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    } finally {
      loading.value = false
    }
  }

  onMounted(load)

  async function create(data: CommitmentCreate): Promise<boolean> {
    try {
      const created = await apiCreate(data)
      commitments.value.push(created)
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  async function update(id: number, data: CommitmentUpdate): Promise<boolean> {
    try {
      const updated = await apiUpdate(id, data)
      const idx = commitments.value.findIndex(commitment => commitment.id === id)
      if (idx >= 0) {
        commitments.value[idx] = updated
      }
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  async function remove(id: number): Promise<boolean> {
    try {
      await apiDelete(id)
      commitments.value = commitments.value.filter(commitment => commitment.id !== id)
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  /** Monthly equivalent for a commitment. */
  function monthlyEquiv(amount: number, freq: string): number {
    const multipliers: Record<string, number> = {
      monthly: 1,
      biweekly: 26 / 12,
      weekly: 52 / 12,
      daily: 365.25 / 12,
      once: 0,
    }
    return amount * (multipliers[freq] ?? 1)
  }

  const parsed = computed(() =>
    commitments.value.map(commitment => ({
      ...commitment,
      parsedAmount: parseMoney(commitment.amount),
    }))
  )

  const totalMonthlyIncome = computed(() =>
    parsed.value
      .filter(commitment => parseMoney(commitment.amount) > 0 && commitment.frequency !== 'once')
      .reduce((total, commitment) => total + monthlyEquiv(parseMoney(commitment.amount), commitment.frequency), 0)
  )

  const totalMonthlyExpenses = computed(() =>
    parsed.value
      .filter(commitment => parseMoney(commitment.amount) < 0 && commitment.frequency !== 'once')
      .reduce((total, commitment) => total + monthlyEquiv(parseMoney(commitment.amount), commitment.frequency), 0)
  )

  const netMonthly = computed(() => totalMonthlyIncome.value + totalMonthlyExpenses.value)

  return {
    commitments,
    loading,
    error,
    load,
    create,
    update,
    remove,
    parsed,
    totalMonthlyIncome,
    totalMonthlyExpenses,
    netMonthly,
  }
}
