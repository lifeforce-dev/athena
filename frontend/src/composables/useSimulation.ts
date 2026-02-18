import { ref, computed } from 'vue'
import { useProjection } from './useProjection'
import { buildTrajectory, type TrajectoryPoint } from '@/utils/trajectory'
import { toLocalDateString, parseLocalDate } from '@/utils/format'

export interface MonthBreak {
  label: string
  startBal: number
  endBal: number
  net: number
  startDate: string
  endDate: string
}

export function useSimulation() {
  const today = new Date()
  const threeMonthsOut = new Date(today.getFullYear(), today.getMonth() + 3, today.getDate())

  const startDate = ref(toLocalDateString(today))
  const endDate = ref(toLocalDateString(threeMonthsOut))
  const hasRun = ref(false)

  const projection = useProjection()

  async function runSimulation() {
    hasRun.value = true
    return projection.load(endDate.value, startDate.value)
  }

  /** Build trajectory array from ledger entries. */
  const trajectory = computed<TrajectoryPoint[]>(() =>
    buildTrajectory(projection.ledger.value)
  )

  const dayWindow = computed(() => {
    const start = parseLocalDate(startDate.value)
    const end = parseLocalDate(endDate.value)
    return Math.round((end.getTime() - start.getTime()) / 86_400_000)
  })

  const currentBalance = computed(() => {
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

  /** Compute monthly breakdown from trajectory. */
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

    // Last partial month.
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
    startDate,
    endDate,
    hasRun,
    loading: projection.loading,
    error: projection.error,
    runSimulation,
    trajectory,
    dayWindow,
    currentBalance,
    afterBalance,
    lowestPoint,
    avgGainedPerMonth,
    monthBreaks,
  }
}
