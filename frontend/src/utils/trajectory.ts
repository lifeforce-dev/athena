/** Shared trajectory-building logic for dashboard and simulation views. */

export interface TrajectoryPoint {
  date: string
  balance: number
  events: { name: string; amount: number }[]
}

interface LedgerLike {
  date: string
  name: string
  delta: number
  balance: number
}

/** Build a trajectory array from parsed ledger entries, grouping events by date. */
export function buildTrajectory(entries: LedgerLike[]): TrajectoryPoint[] {
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
}
