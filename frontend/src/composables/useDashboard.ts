import { computed, ref, onMounted } from 'vue'
import { useProjection } from './useProjection'
import { buildTrajectory, type TrajectoryPoint } from '@/utils/trajectory'
import { toLocalDateString } from '@/utils/format'
import { fetchDemoProjection } from '@/api/demo-data'
import { demoTourActive } from '@/stores/demoTour'

export type { TrajectoryPoint } from '@/utils/trajectory'

export function useDashboard() {
  const today = new Date()
  const ninetyDaysOut = new Date(today.getTime() + 90 * 24 * 60 * 60 * 1000)

  const fromDate = ref(toLocalDateString(today))
  const asOf = ref(toLocalDateString(ninetyDaysOut))

  const projection = useProjection()

  async function refresh() {
    console.info('[TourDebug][useDashboard] Refresh started', {
      demoTourActive: demoTourActive.value,
      fromDate: fromDate.value,
      asOf: asOf.value,
    })

    // During a guided tour, load demo data so the dashboard has content.
    if (demoTourActive.value) {
      projection.loading.value = true
      projection.error.value = null
      try {
        projection.data.value = await fetchDemoProjection()
        console.info('[TourDebug][useDashboard] Loaded demo projection', {
          ledgerCount: projection.data.value.ledger.length,
          monthCount: projection.data.value.months.length,
          currentBalance: projection.data.value.current_balance,
        })
        return
      } catch (err) {
        console.error('[useDashboard] Demo data fetch failed:', err)
      } finally {
        projection.loading.value = false
      }
    }

    console.info('[TourDebug][useDashboard] Loading real projection endpoint')
    return projection.load(asOf.value, fromDate.value)
  }

  onMounted(refresh)

  /** Build trajectory array from ledger entries. */
  const trajectory = computed<TrajectoryPoint[]>(() =>
    buildTrajectory(projection.ledger.value)
  )

  /** Current balance from projection. */
  const currentBalance = computed(() => projection.currentBalance.value)

  /** Whether the user has a real balance (from bank or manual entry). */
  const hasInitialBalance = computed(() => projection.hasInitialBalance.value)

  /** Backend-computed risk analysis (expenses-before-income walk). */
  const riskAnalysis = computed(() => projection.riskAnalysis.value)

  /** End balance (last trajectory point). */
  const endBalance = computed(() => {
    const points = trajectory.value
    return points.length ? points[points.length - 1].balance : 0
  })

  /** Net change over the projection window. */
  const netChange = computed(() => endBalance.value - currentBalance.value)

  /** Calendar days in the projection window. */
  const daysCovered = computed(() => {
    const first = new Date(fromDate.value + 'T12:00:00').getTime()
    const last = new Date(asOf.value + 'T12:00:00').getTime()
    return Math.round((last - first) / (24 * 60 * 60 * 1000))
  })

  return {
    ...projection,
    fromDate,
    asOf,
    refresh,
    trajectory,
    riskAnalysis,
    currentBalance,
    hasInitialBalance,
    endBalance,
    netChange,
    daysCovered,
  }
}
