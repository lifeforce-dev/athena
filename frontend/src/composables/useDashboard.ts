import { computed, ref, onMounted } from 'vue'
import { useProjection } from './useProjection'
import { toLocalDateString } from '@/utils/format'

/** Derived trajectory point for chart/event display. */
export interface TrajectoryPoint {
  date: string
  balance: number
  events: { name: string; amount: number }[]
}

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

  /** Lowest balance point in the trajectory. */
  const lowestPoint = computed(() => {
    if (!trajectory.value.length) return null
    return trajectory.value.reduce((min, pt) => (pt.balance < min.balance ? pt : min))
  })

  /** Current balance from projection. */
  const currentBalance = computed(() => projection.currentBalance.value)

  /** End balance (last trajectory point). */
  const endBalance = computed(() => {
    const t = trajectory.value
    return t.length ? t[t.length - 1].balance : 0
  })

  /** Net change over the projection window. */
  const netChange = computed(() => endBalance.value - currentBalance.value)

  /** Calendar days covered by the projection window. */
  const daysCovered = computed(() => {
    const t = trajectory.value
    if (t.length < 2) return t.length
    const first = new Date(t[0].date + 'T12:00:00').getTime()
    const last = new Date(t[t.length - 1].date + 'T12:00:00').getTime()
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
