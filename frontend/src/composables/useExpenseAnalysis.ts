import { computed } from 'vue'
import type { Ref } from 'vue'
import type { TrajectoryPoint } from './useDashboard'
import { toLocalDateString, parseLocalDate } from '@/utils/format'

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
    const T = trajectory.value
    if (!T.length) return null

    // Identify paycheck indices (income > 500).
    const payIndices: number[] = []
    T.forEach((t, i) => {
      if (t.events.some(e => e.amount > 500)) payIndices.push(i)
    })
    if (payIndices.length && payIndices[0] > 0) payIndices.unshift(0)
    if (!payIndices.length) payIndices.push(0)

    let worst: WorstWindow | null = null

    for (let w = 0; w < payIndices.length; w++) {
      const start = payIndices[w]
      const end = w + 1 < payIndices.length ? payIndices[w + 1] - 1 : T.length - 1
      const window = T.slice(start, end + 1)
      const expenses: WorstWindowExpense[] = []
      let totalExp = 0
      let minBal = Infinity
      let minDate = ''
      let income = 0

      for (const t of window) {
        if (t.balance < minBal) {
          minBal = t.balance
          minDate = t.date
        }
        for (const e of t.events) {
          if (e.amount > 0) {
            income += e.amount
          } else {
            expenses.push({ name: e.name, amount: Math.abs(e.amount), date: t.date })
            totalExp += Math.abs(e.amount)
          }
        }
      }

      expenses.sort((a, b) => b.amount - a.amount)

      const data: WorstWindow = {
        startDate: T[start].date,
        endDate: T[end].date,
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
    const T = trajectory.value
    const wave: number[] = []
    let cumExp = 0

    for (const t of T) {
      if (t.events.some(e => e.amount > 500)) cumExp = 0
      for (const e of t.events) {
        if (e.amount < 0) cumExp += Math.abs(e.amount)
      }
      wave.push(cumExp)
    }

    return wave
  })

  /** Per-day breakdown of accumulated expenses since last paycheck. */
  const dailyExpenseStack = computed<DailyExpenseEntry[][]>(() => {
    const T = trajectory.value
    const stacks: DailyExpenseEntry[][] = []
    let currentWindowExpenses: DailyExpenseEntry[] = []

    for (const t of T) {
      if (t.events.some(e => e.amount > 500)) currentWindowExpenses = []
      for (const e of t.events) {
        if (e.amount < 0) {
          currentWindowExpenses.push({
            name: e.name,
            amount: Math.abs(e.amount),
            date: t.date,
          })
        }
      }
      stacks.push(
        [...currentWindowExpenses].sort((a, b) => b.amount - a.amount)
      )
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
    const T = trajectory.value
    if (!T.length) return { bills: [] as BillEntry[], nextBills: [] as BillEntry[], nextWeekStart: '' }

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
    const weStr = toLocalDateString(weekEnd)
    const nsStr = toLocalDateString(nextStart)
    const neStr = toLocalDateString(nextEnd)

    const bills: BillEntry[] = []
    const nextBills: BillEntry[] = []

    for (const t of T) {
      for (const e of t.events) {
        if (e.amount >= 0) continue
        if (t.date >= todayStr && t.date <= weStr) {
          bills.push({ name: e.name, amount: Math.abs(e.amount), date: t.date })
        }
        if (t.date >= nsStr && t.date <= neStr) {
          nextBills.push({ name: e.name, amount: Math.abs(e.amount), date: t.date })
        }
      }
    }

    return { bills, nextBills, nextWeekStart: nsStr }
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
