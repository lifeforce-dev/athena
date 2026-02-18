import { computed } from 'vue'
import type { Ref } from 'vue'
import type { TrajectoryPoint } from '@/utils/trajectory'
import { toLocalDateString, parseLocalDate } from '@/utils/format'
import { PAYCHECK_INCOME_THRESHOLD } from '@/utils/constants'

// ── Types ──

export interface WorstWindowExpense {
  name: string
  amount: number
  date: string
}

export interface WorstWindow {
  startDate: string
  endDate: string
  startIdx: number
  endIdx: number
  minBal: number
  minDate: string
  totalExpenses: number
  income: number
  expenses: WorstWindowExpense[]
  pctOfIncome: number
}

export interface DailyExpenseEntry {
  name: string
  amount: number
  date: string
}

export interface BillEntry {
  name: string
  amount: number
  date: string
}

// ── Cause palette (shared by CausePanel + chart bands) ──

export const CAUSE_COLORS = [
  '#F87171', '#FB923C', '#FBBF24', '#A78BFA', '#60A5FA',
  '#34D399', '#F472B6', '#94A3B8',
]

// ── Composable ──

export function useExpenseAnalysis(trajectory: Ref<TrajectoryPoint[]>) {

  /** Find the pay period with the lowest minimum balance. */
  const worstWindow = computed<WorstWindow | null>(() => {
    const points = trajectory.value
    if (!points.length) return null

    // Identify paycheck indices (income above threshold).
    const payIndices: number[] = []
    points.forEach((point, i) => {
      if (point.events.some(event => event.amount > PAYCHECK_INCOME_THRESHOLD)) payIndices.push(i)
    })
    if (payIndices.length && payIndices[0] > 0) payIndices.unshift(0)
    if (!payIndices.length) payIndices.push(0)

    let worst: WorstWindow | null = null

    for (let windowIdx = 0; windowIdx < payIndices.length; windowIdx++) {
      const start = payIndices[windowIdx]
      const end = windowIdx + 1 < payIndices.length ? payIndices[windowIdx + 1] - 1 : points.length - 1
      const window = points.slice(start, end + 1)
      const expenses: WorstWindowExpense[] = []
      let totalExp = 0
      let minBal = Infinity
      let minDate = ''
      let income = 0

      for (const point of window) {
        if (point.balance < minBal) {
          minBal = point.balance
          minDate = point.date
        }
        for (const event of point.events) {
          if (event.amount > 0) {
            income += event.amount
          } else {
            expenses.push({ name: event.name, amount: Math.abs(event.amount), date: point.date })
            totalExp += Math.abs(event.amount)
          }
        }
      }

      expenses.sort((a, b) => b.amount - a.amount)

      const data: WorstWindow = {
        startDate: points[start].date,
        endDate: points[end].date,
        startIdx: start,
        endIdx: end,
        minBal,
        minDate,
        totalExpenses: totalExp,
        income,
        expenses,
        pctOfIncome: income > 0 ? Math.round((totalExp / income) * 100) : 0,
      }

      if (!worst || minBal < worst.minBal) worst = data
    }

    return worst
  })

  /** Cumulative expense wave per day (resets at each paycheck). */
  const expenseWave = computed<number[]>(() => {
    const points = trajectory.value
    const wave: number[] = []
    let cumExp = 0

    for (const point of points) {
      if (point.events.some(event => event.amount > PAYCHECK_INCOME_THRESHOLD)) cumExp = 0
      for (const event of point.events) {
        if (event.amount < 0) cumExp += Math.abs(event.amount)
      }
      wave.push(cumExp)
    }

    return wave
  })

  /** Per-day breakdown of accumulated expenses since last paycheck, aggregated by name. */
  const dailyExpenseStack = computed<DailyExpenseEntry[][]>(() => {
    const points = trajectory.value
    const stacks: DailyExpenseEntry[][] = []
    let windowTotals = new Map<string, number>()

    for (const point of points) {
      if (point.events.some(event => event.amount > PAYCHECK_INCOME_THRESHOLD)) {
        windowTotals = new Map()
      }

      for (const event of point.events) {
        if (event.amount < 0) {
          const prev = windowTotals.get(event.name) ?? 0
          windowTotals.set(event.name, prev + Math.abs(event.amount))
        }
      }

      const dayStack: DailyExpenseEntry[] = Array.from(windowTotals.entries())
        .map(([name, amount]) => ({ name, amount, date: point.date }))
        .sort((a, b) => b.amount - a.amount)
      stacks.push(dayStack)
    }

    return stacks
  })

  /** Stable ordering of expense names by max amount (largest first). */
  const masterExpenseOrder = computed<string[]>(() => {
    const amounts: Record<string, number> = {}
    const order: string[] = []

    for (const stack of dailyExpenseStack.value) {
      for (const exp of stack) {
        if (!(exp.name in amounts)) {
          amounts[exp.name] = 0
          order.push(exp.name)
        }
        amounts[exp.name] = Math.max(amounts[exp.name], exp.amount)
      }
    }

    order.sort((a, b) => amounts[b] - amounts[a])
    return order
  })

  /** Consistent color map: expense name -> hex color. */
  const masterColorMap = computed<Record<string, string>>(() => {
    const map: Record<string, string> = {}
    masterExpenseOrder.value.forEach((name, i) => {
      map[name] = CAUSE_COLORS[i % CAUSE_COLORS.length]
    })
    return map
  })

  /** Bills due in the current week and next week. */
  const billsAnalysis = computed(() => {
    const points = trajectory.value
    if (!points.length) return { bills: [] as BillEntry[], nextBills: [] as BillEntry[], nextWeekStart: '' }

    const now = new Date()
    const day = now.getDay()

    // Current week ends Saturday.
    const weekEnd = new Date(now)
    weekEnd.setDate(now.getDate() + (6 - day))

    // Next week boundaries.
    const nextStart = new Date(weekEnd)
    nextStart.setDate(weekEnd.getDate() + 1)
    const nextEnd = new Date(nextStart)
    nextEnd.setDate(nextStart.getDate() + 6)

    const todayStr = toLocalDateString(now)
    const weekEndStr = toLocalDateString(weekEnd)
    const nextStartStr = toLocalDateString(nextStart)
    const nextEndStr = toLocalDateString(nextEnd)

    const bills: BillEntry[] = []
    const nextBills: BillEntry[] = []

    for (const point of points) {
      for (const event of point.events) {
        if (event.amount >= 0) continue
        if (point.date >= todayStr && point.date <= weekEndStr) {
          bills.push({ name: event.name, amount: Math.abs(event.amount), date: point.date })
        }
        if (point.date >= nextStartStr && point.date <= nextEndStr) {
          nextBills.push({ name: event.name, amount: Math.abs(event.amount), date: point.date })
        }
      }
    }

    return { bills, nextBills, nextWeekStart: nextStartStr }
  })

  return {
    worstWindow,
    expenseWave,
    dailyExpenseStack,
    masterExpenseOrder,
    masterColorMap,
    billsAnalysis,
  }
}
