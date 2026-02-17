import { ref, computed } from 'vue'
import { useProjection } from './useProjection'
import type { TrajectoryPoint } from './useDashboard'
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
  const trajectory = computed<TrajectoryPoint[]>(() => {
    const entries = projection.ledger.value
    if (!entries.length) return []

    const byDate = new Map<string, { balance: number; events: { name: string; amount: number }[] }>()

    for (const entry of entries) {
      const existing = byDate.get(entry.date)
      if (existing) {
        existing.balance = entry.balance
        existing.events.push({ name: entry.name, amount: entry.delta })
      } else {
        byDate.set(entry.date, {
          balance: entry.balance,
          events: [{ name: entry.name, amount: entry.delta }],
        })
      }
    }

    return Array.from(byDate.entries()).map(([date, data]) => ({
      date,
      balance: data.balance,
      events: data.events,
    }))
  })

  const dayWindow = computed(() => {
    const s = parseLocalDate(startDate.value)
    const e = parseLocalDate(endDate.value)
    return Math.round((e.getTime() - s.getTime()) / 86_400_000)
  })

  const currentBalance = computed(() => {
    const t = trajectory.value
    return t.length ? t[0].balance : 0
  })

  const afterBalance = computed(() => {
    const t = trajectory.value
    return t.length ? t[t.length - 1].balance : 0
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
    const t = trajectory.value
    if (t.length < 2) return []

    const breaks: MonthBreak[] = []
    let curMonth = t[0].date.slice(0, 7)
    let monthStartIdx = 0

    const shortLabel = (d: string) =>
      parseLocalDate(d).toLocaleDateString('en-US', { month: 'short', year: '2-digit' })

    for (let i = 1; i < t.length; i++) {
      const m = t[i].date.slice(0, 7)
      if (m !== curMonth) {
        breaks.push({
          label: shortLabel(t[monthStartIdx].date),
          startBal: t[monthStartIdx].balance,
          endBal: t[i - 1].balance,
          net: t[i - 1].balance - t[monthStartIdx].balance,
          startDate: t[monthStartIdx].date,
          endDate: t[i - 1].date,
        })
        monthStartIdx = i
        curMonth = m
      }
    }

    // Last partial month.
    breaks.push({
      label: shortLabel(t[monthStartIdx].date),
      startBal: t[monthStartIdx].balance,
      endBal: t[t.length - 1].balance,
      net: t[t.length - 1].balance - t[monthStartIdx].balance,
      startDate: t[monthStartIdx].date,
      endDate: t[t.length - 1].date,
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
