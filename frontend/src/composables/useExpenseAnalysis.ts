import { computed } from 'vue'
import type { Ref } from 'vue'
import type { TrajectoryPoint } from '@/utils/trajectory'
import { toLocalDateString } from '@/utils/format'
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

export interface Shortfall {
  brokeDate: string
  brokeBalance: number
  missedCommitments: { name: string; amount: number; date: string }[]
  recoveryDate: string | null
  totalMissed: number
}

// ── Cause palette (shared by CausePanel + chart bands) ──

export const CAUSE_COLORS = [
  '#F87171', '#FB923C', '#FBBF24', '#A78BFA', '#60A5FA',
  '#34D399', '#F472B6', '#94A3B8',
]

// ── Helpers ──

/** A point marks a paycheck boundary if any event exceeds the income threshold. */
function isPaycheck(point: TrajectoryPoint): boolean {
  return point.events.some(event => event.amount > PAYCHECK_INCOME_THRESHOLD)
}

/** Index boundary for a single paycheck-to-paycheck window. */
interface PayWindow {
  start: number
  end: number
}

/** Analyze a single paycheck-to-paycheck window slice of the trajectory. */
function analyzeWindow(points: TrajectoryPoint[], start: number, end: number): WorstWindow {
  let minBal = Infinity
  let minDate = ''
  let income = 0

  const expenses: WorstWindowExpense[] = []
  let totalExp = 0

  for (let i = start; i <= end; i++) {
    const point = points[i]

    if (point.balance < minBal) {
      minBal = point.balance
      minDate = point.date
    }

    for (const event of point.events) {
      if (event.amount > 0) {
        income += event.amount
      } else {
        const amt = -event.amount
        expenses.push({ name: event.name, amount: amt, date: point.date })
        totalExp += amt
      }
    }
  }

  expenses.sort((a, b) => b.amount - a.amount)

  return {
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
}

// ── Composable ──

export function useExpenseAnalysis(
  trajectory: Ref<TrajectoryPoint[]>,
  /** Backend-computed date when balance goes negative (expenses-before-income). */
  negativeDate?: Ref<string | null>,
  /** Backend-computed balance at the negative date. */
  negativeBalance?: Ref<number | null>,
) {

  // Segment trajectory into paycheck-to-paycheck windows.
  // If no paychecks exist, the entire trajectory is treated as one window.
  const paycheckWindows = computed<PayWindow[]>(() => {
    const points = trajectory.value
    if (!points.length) return []

    const starts: number[] = [0]
    for (let i = 1; i < points.length; i++) {
      if (isPaycheck(points[i])) starts.push(i)
    }

    return starts.map((s, idx) => ({
      start: s,
      end: idx + 1 < starts.length ? starts[idx + 1] - 1 : points.length - 1,
    }))
  })

  /** Find the pay period with the lowest minimum balance. */
  const worstWindow = computed<WorstWindow | null>(() => {
    const points = trajectory.value
    const windows = paycheckWindows.value
    if (!windows.length) return null

    let worst: WorstWindow | null = null

    for (const { start, end } of windows) {
      const data = analyzeWindow(points, start, end)
      if (!worst || data.minBal < worst.minBal) worst = data
    }

    return worst
  })

  /** Cumulative expense wave per day (resets at each paycheck). */
  const expenseWave = computed<number[]>(() => {
    const points = trajectory.value
    const wave: number[] = []
    let cumExp = 0

    for (const point of points) {
      if (isPaycheck(point)) cumExp = 0
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
      if (isPaycheck(point)) windowTotals = new Map()

      for (const event of point.events) {
        if (event.amount < 0) {
          const prev = windowTotals.get(event.name) ?? 0
          windowTotals.set(event.name, prev + Math.abs(event.amount))
        }
      }

      // No per-day sort needed: masterExpenseOrder controls rendering order.
      stacks.push(
        Array.from(windowTotals.entries())
          .map(([name, amount]) => ({ name, amount, date: point.date }))
      )
    }

    return stacks
  })

  /** Stable ordering + color map for expense names, computed in a single pass. */
  const expensePresentation = computed(() => {
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

    const colorMap: Record<string, string> = {}
    order.forEach((name, i) => {
      colorMap[name] = CAUSE_COLORS[i % CAUSE_COLORS.length]
    })

    return { order, colorMap }
  })

  const masterExpenseOrder = computed(() => expensePresentation.value.order)
  const masterColorMap = computed(() => expensePresentation.value.colorMap)

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

  /**
   * Detect first point where balance goes negative.
   *
   * Uses the backend's expenses-before-income analysis (negativeDate)
   * to identify the date, then scans the trajectory for affected
   * commitments to build the missed-commitments list.
   */
  const shortfall = computed<Shortfall | null>(() => {
    const points = trajectory.value
    if (!points.length) return null

    const brokeDate = negativeDate?.value
    const brokeBal = negativeBalance?.value
    if (!brokeDate || brokeBal == null) return null

    // Find the trajectory index at or after the broke date.
    const brokeIdx = points.findIndex(p => p.date >= brokeDate)
    if (brokeIdx < 0) return null

    const missed: { name: string; amount: number; date: string }[] = []
    let recoveryDate: string | null = null

    // Collect expenses from the broke date forward until the next paycheck.
    for (let i = brokeIdx; i < points.length; i++) {
      if (isPaycheck(points[i]) && i > brokeIdx) {
        recoveryDate = points[i].date
        break
      }

      for (const event of points[i].events) {
        if (event.amount < 0) {
          missed.push({ name: event.name, amount: Math.abs(event.amount), date: points[i].date })
        }
      }
    }

    return {
      brokeDate,
      brokeBalance: brokeBal,
      missedCommitments: missed,
      recoveryDate,
      totalMissed: missed.reduce((sum, m) => sum + m.amount, 0),
    }
  })

  return {
    worstWindow,
    expenseWave,
    dailyExpenseStack,
    masterExpenseOrder,
    masterColorMap,
    billsAnalysis,
    shortfall,
  }
}
