/**
 * Tests for shortfall detection in useExpenseAnalysis.
 *
 * The shortfall computed uses expenses-before-income ordering per day
 * so that a same-day paycheck does not mask an intra-day dip below zero.
 * The bug this catches: backend sorts paychecks before expenses on the
 * same date, producing an end-of-day balance that never goes negative
 * even though the user cannot actually cover their bills without the
 * paycheck arriving first.
 */
import { describe, it, expect } from 'vitest'
import { ref } from 'vue'
import { useExpenseAnalysis } from '@/composables/useExpenseAnalysis'
import type { TrajectoryPoint } from '@/utils/trajectory'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a minimal trajectory point. */
function point(
  date: string,
  balance: number,
  events: { name: string; amount: number }[],
): TrajectoryPoint {
  return { date, balance, events }
}

// ---------------------------------------------------------------------------
// shortfall
// ---------------------------------------------------------------------------

describe('shortfall detection', () => {
  it('detects shortfall when same-day paycheck masks negative balance', () => {
    // Trajectory as the backend delivers it: paycheck sorted first,
    // so end-of-day balance stays positive ($100 + $3700 - $2100 = $1700).
    const trajectory = ref<TrajectoryPoint[]>([
      point('2026-02-20', 3800, [
        { name: 'Paycheck', amount: 3700 },
        { name: 'Rent', amount: -2100 },
      ]),
      point('2026-02-25', 3500, [
        { name: 'Internet', amount: -83 },
        { name: 'Phone', amount: -55 },
      ]),
    ])
    const currentBalance = ref(100)

    const { shortfall } = useExpenseAnalysis(trajectory, currentBalance)

    // Expenses-first: $100 - $2100 = -$2000 before paycheck lands.
    expect(shortfall.value).not.toBeNull()
    expect(shortfall.value!.brokeDate).toBe('2026-02-20')
    expect(shortfall.value!.brokeBalance).toBe(-2000)
  })

  it('returns null when balance never goes negative', () => {
    const trajectory = ref<TrajectoryPoint[]>([
      point('2026-02-20', 2700, [{ name: 'Rent', amount: -2100 }]),
      point('2026-02-22', 2600, [{ name: 'Internet', amount: -83 }]),
    ])
    const currentBalance = ref(5000)

    const { shortfall } = useExpenseAnalysis(trajectory, currentBalance)

    expect(shortfall.value).toBeNull()
  })

  it('returns null for empty trajectory', () => {
    const trajectory = ref<TrajectoryPoint[]>([])
    const currentBalance = ref(1000)

    const { shortfall } = useExpenseAnalysis(trajectory, currentBalance)

    expect(shortfall.value).toBeNull()
  })

  it('detects shortfall on a day with only expenses', () => {
    const trajectory = ref<TrajectoryPoint[]>([
      point('2026-03-01', -1950, [
        { name: 'Rent', amount: -2100 },
        { name: 'Gym', amount: -35 },
      ]),
      point('2026-03-05', -2033, [{ name: 'Internet', amount: -83 }]),
      point('2026-03-13', 1667, [{ name: 'Paycheck', amount: 3700 }]),
    ])
    const currentBalance = ref(150)

    const { shortfall } = useExpenseAnalysis(trajectory, currentBalance)

    expect(shortfall.value).not.toBeNull()
    expect(shortfall.value!.brokeDate).toBe('2026-03-01')
    // $150 - $2100 = -$1950, then -$35 = -$1985
    expect(shortfall.value!.brokeBalance).toBe(-1985)
  })

  it('collects missed commitments until next paycheck', () => {
    const trajectory = ref<TrajectoryPoint[]>([
      point('2026-02-20', -45, [{ name: 'Electric', amount: -145 }]),
      point('2026-02-22', -225, [
        { name: 'Groceries', amount: -120 },
        { name: 'Adobe', amount: -60 },
      ]),
      point('2026-02-27', 3406, [
        { name: 'Gas', amount: -65 },
        { name: 'Paycheck', amount: 3700 },
      ]),
    ])
    const currentBalance = ref(100)

    const { shortfall } = useExpenseAnalysis(trajectory, currentBalance)

    expect(shortfall.value).not.toBeNull()
    expect(shortfall.value!.missedCommitments).toHaveLength(3)
    expect(shortfall.value!.missedCommitments.map(m => m.name)).toEqual([
      'Electric', 'Groceries', 'Adobe',
    ])
    expect(shortfall.value!.recoveryDate).toBe('2026-02-27')
    expect(shortfall.value!.totalMissed).toBe(145 + 120 + 60)
  })

  it('sets recoveryDate to null when no paycheck follows', () => {
    const trajectory = ref<TrajectoryPoint[]>([
      point('2026-03-01', -100, [{ name: 'Rent', amount: -2100 }]),
      point('2026-03-05', -183, [{ name: 'Internet', amount: -83 }]),
    ])
    const currentBalance = ref(2000)

    const { shortfall } = useExpenseAnalysis(trajectory, currentBalance)

    expect(shortfall.value).not.toBeNull()
    expect(shortfall.value!.recoveryDate).toBeNull()
    expect(shortfall.value!.missedCommitments).toHaveLength(2)
  })
})
