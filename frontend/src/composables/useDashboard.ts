import { computed, ref, onMounted } from 'vue'
import { useProjection } from './useProjection'
import { buildTrajectory, type TrajectoryPoint } from '@/utils/trajectory'
import { toLocalDateString } from '@/utils/format'

export type { TrajectoryPoint } from '@/utils/trajectory'

export function useDashboard() {
  const today = new Date()
  const ninetyDaysOut = new Date(today.getTime() + 90 * 24 * 60 * 60 * 1000)

  const fromDate = ref(toLocalDateString(today))
  const asOf = ref(toLocalDateString(ninetyDaysOut))

  const projection = useProjection()

  function refresh() {
    return projection.load(asOf.value, fromDate.value)
  }

  onMounted(refresh)

  /** Build trajectory array from ledger entries. */
  const trajectory = computed<TrajectoryPoint[]>(() =>
    buildTrajectory(projection.ledger.value)
  )

  /** Lowest balance point in the trajectory. */
  const lowestPoint = computed(() => {
    if (!trajectory.value.length) return null
    return trajectory.value.reduce((min, pt) => (pt.balance < min.balance ? pt : min))
  })

  /** Current balance from projection. */
  const currentBalance = computed(() => projection.currentBalance.value)

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
    lowestPoint,
    currentBalance,
    endBalance,
    netChange,
    daysCovered,
  }
}
