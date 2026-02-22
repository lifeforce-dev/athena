import { ref, computed, onMounted } from 'vue'
import type { CommitmentResponse } from '@/types/commitment'
import { fetchCommitments } from '@/api/commitments'
import { fetchDemoCommitments } from '@/api/demo-data'
import { demoTourActive } from '@/stores/demoTour'
import { fetchScenarioProjection, type ScenarioRequest } from '@/api/projection'
import { buildTrajectory, type TrajectoryPoint } from '@/utils/trajectory'
import { toLocalDateString, parseLocalDate, parseMoney } from '@/utils/format'
import type { ParsedLedgerEntry } from '@/types/projection'

export interface ScenarioOverride {
  /** False = commitment excluded from scenario. */
  active: boolean
  /** Overridden amount, or null if unchanged. */
  amount: number | null
}

export interface MonthBreak {
  label: string
  startBal: number
  endBal: number
  net: number
  startDate: string
  endDate: string
}

export function useScenario() {
  // ── Commitments ──
  const commitments = ref<CommitmentResponse[]>([])
  const commitmentsLoading = ref(false)
  const commitmentsError = ref<string | null>(null)

  /** Per-commitment overrides keyed by commitment ID. */
  const overrides = ref<Map<number, ScenarioOverride>>(new Map())

  async function loadCommitments() {
    commitmentsLoading.value = true
    commitmentsError.value = null
    try {
      commitments.value = demoTourActive.value
        ? await fetchDemoCommitments()
        : await fetchCommitments()
      // Initialize overrides for any new commitments.
      for (const commitment of commitments.value) {
        if (!overrides.value.has(commitment.id)) {
          overrides.value.set(commitment.id, { active: true, amount: null })
        }
      }
    } catch (err) {
      commitmentsError.value = err instanceof Error ? err.message : String(err)
    } finally {
      commitmentsLoading.value = false
    }
  }

  onMounted(async () => {
    await loadCommitments()

    // During FTE, auto-run the simulation so the chart is visible for the tour.
    if (demoTourActive.value) {
      await runSimulation()
    }
  })

  // ── Toggle & edit helpers ──

  function toggleCommitment(id: number) {
    const current = overrides.value.get(id)
    if (current) {
      current.active = !current.active
    }
  }

  function setAmountOverride(id: number, amount: number) {
    const current = overrides.value.get(id)
    if (!current) return
    const original = parseMoney(
      commitments.value.find(commitment => commitment.id === id)?.amount ?? '0',
    )
    // Clear override if value matches original.
    current.amount = amount === original ? null : amount
  }

  function resetOverrides() {
    for (const override of overrides.value.values()) {
      override.active = true
      override.amount = null
    }
  }

  // ── Derived scenario stats ──

  /** Monthly equivalent for a given frequency. */
  function monthlyEquiv(amount: number, freq: string): number {
    const multipliers: Record<string, number> = {
      monthly: 1, biweekly: 26 / 12, weekly: 52 / 12, daily: 365.25 / 12, once: 0,
    }
    return amount * (multipliers[freq] ?? 1)
  }

  /** Effective amount for a commitment (override or original). */
  function effectiveAmount(commitment: CommitmentResponse): number {
    const override = overrides.value.get(commitment.id)
    if (override?.amount != null) return override.amount
    return parseMoney(commitment.amount)
  }

  const activeCommitments = computed(() =>
    commitments.value.filter(commitment => overrides.value.get(commitment.id)?.active !== false),
  )

  const excludedIds = computed(() =>
    commitments.value
      .filter(commitment => overrides.value.get(commitment.id)?.active === false)
      .map(commitment => commitment.id),
  )

  const amountOverrides = computed(() => {
    const result: Record<number, string> = {}
    for (const [id, override] of overrides.value) {
      if (override.amount != null) {
        result[id] = String(override.amount)
      }
    }
    return result
  })

  const scenarioIncome = computed(() =>
    activeCommitments.value
      .filter(commitment => parseMoney(commitment.amount) > 0 && commitment.frequency !== 'once')
      .reduce((total, commitment) => total + monthlyEquiv(effectiveAmount(commitment), commitment.frequency), 0),
  )

  const scenarioExpenses = computed(() =>
    activeCommitments.value
      .filter(commitment => parseMoney(commitment.amount) < 0 && commitment.frequency !== 'once')
      .reduce((total, commitment) => total + monthlyEquiv(effectiveAmount(commitment), commitment.frequency), 0),
  )

  const scenarioNet = computed(() => scenarioIncome.value + scenarioExpenses.value)

  const disabledCount = computed(() => excludedIds.value.length)

  const editedCount = computed(() =>
    [...overrides.value.values()].filter(override => override.amount != null).length,
  )

  const hasChanges = computed(() => disabledCount.value > 0 || editedCount.value > 0)

  // Monthly savings from disabled recurring expenses.
  const savingsFromCuts = computed(() =>
    commitments.value
      .filter(commitment =>
        overrides.value.get(commitment.id)?.active === false
        && parseMoney(commitment.amount) < 0
        && commitment.frequency !== 'once',
      )
      .reduce((total, commitment) =>
        total + Math.abs(monthlyEquiv(parseMoney(commitment.amount), commitment.frequency)), 0),
  )

  // ── Simulation dates & projection ──
  const today = new Date()
  const threeMonthsOut = new Date(today.getFullYear(), today.getMonth() + 3, today.getDate())

  const startDate = ref(toLocalDateString(today))
  const endDate = ref(toLocalDateString(threeMonthsOut))
  const hasRun = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const dayWindow = computed(() => {
    const start = parseLocalDate(startDate.value)
    const end = parseLocalDate(endDate.value)
    return Math.round((end.getTime() - start.getTime()) / 86_400_000)
  })

  const ledger = ref<ParsedLedgerEntry[]>([])
  const apiBalance = ref<number | null>(null)

  async function runSimulation() {
    hasRun.value = true
    loading.value = true
    error.value = null
    try {
      const body: ScenarioRequest = {
        as_of: endDate.value,
        from_date: startDate.value,
        excluded_ids: excludedIds.value,
        amount_overrides: amountOverrides.value,
      }
      const response = await fetchScenarioProjection(body)

      apiBalance.value = parseMoney(response.current_balance)

      ledger.value = (response.ledger ?? []).map(entry => ({
        date: entry.date,
        name: entry.name,
        delta: parseMoney(entry.delta),
        balance: parseMoney(entry.balance),
      }))
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    } finally {
      loading.value = false
    }
  }

  const trajectory = computed<TrajectoryPoint[]>(() => buildTrajectory(ledger.value))

  const currentBalance = computed(() => {
    if (apiBalance.value !== null) return apiBalance.value
    const points = trajectory.value
    return points.length ? points[0].balance : 0
  })

  const afterBalance = computed(() => {
    const points = trajectory.value
    return points.length ? points[points.length - 1].balance : 0
  })

  const lowestPoint = computed(() => {
    if (!trajectory.value.length) return null
    return trajectory.value.reduce((min, pt) => (pt.balance < min.balance ? pt : min))
  })

  const avgGainedPerMonth = computed(() => {
    const net = afterBalance.value - currentBalance.value
    const months = Math.max(dayWindow.value / 30.44, 1)
    return net / months
  })

  const monthBreaks = computed<MonthBreak[]>(() => {
    const points = trajectory.value
    if (points.length < 2) return []

    const breaks: MonthBreak[] = []
    let curMonth = points[0].date.slice(0, 7)
    let monthStartIdx = 0

    const shortLabel = (dateStr: string) =>
      parseLocalDate(dateStr).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })

    for (let i = 1; i < points.length; i++) {
      const monthKey = points[i].date.slice(0, 7)
      if (monthKey !== curMonth) {
        breaks.push({
          label: shortLabel(points[monthStartIdx].date),
          startBal: points[monthStartIdx].balance,
          endBal: points[i - 1].balance,
          net: points[i - 1].balance - points[monthStartIdx].balance,
          startDate: points[monthStartIdx].date,
          endDate: points[i - 1].date,
        })
        monthStartIdx = i
        curMonth = monthKey
      }
    }

    breaks.push({
      label: shortLabel(points[monthStartIdx].date),
      startBal: points[monthStartIdx].balance,
      endBal: points[points.length - 1].balance,
      net: points[points.length - 1].balance - points[monthStartIdx].balance,
      startDate: points[monthStartIdx].date,
      endDate: points[points.length - 1].date,
    })

    return breaks
  })

  return {
    // Commitments
    commitments,
    commitmentsLoading,
    commitmentsError,
    overrides,
    toggleCommitment,
    setAmountOverride,
    resetOverrides,
    effectiveAmount,

    // Scenario stats
    scenarioIncome,
    scenarioExpenses,
    scenarioNet,
    disabledCount,
    editedCount,
    hasChanges,
    savingsFromCuts,

    // Simulation
    startDate,
    endDate,
    dayWindow,
    hasRun,
    loading,
    error,
    runSimulation,
    trajectory,
    currentBalance,
    afterBalance,
    lowestPoint,
    avgGainedPerMonth,
    monthBreaks,
  }
}
