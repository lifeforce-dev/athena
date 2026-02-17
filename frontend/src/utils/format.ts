export const formatCurrency = (value: number): string =>
  value.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 })

export const formatSigned = (value: number): string => {
  const sign = value >= 0 ? '+' : '-'
  return `${sign}${formatCurrency(Math.abs(value))}`
}

/**
 * Parse a Decimal string from the API into a number for display.
 * The backend serializes Decimal as JSON strings to avoid IEEE 754 loss.
 */
export const parseMoney = (value: string): number => Number(value)

/**
 * Format a Date as a local YYYY-MM-DD string without UTC conversion.
 * Avoids the timezone off-by-one bug from Date.toISOString().slice(0, 10).
 */
export const toLocalDateString = (d: Date): string => {
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

/**
 * Parse a YYYY-MM-DD string as a local date (not UTC).
 * Using new Date('YYYY-MM-DD') interprets it as UTC midnight, which shifts
 * the displayed day by -1 for users west of UTC.
 */
export const parseLocalDate = (dateStr: string): Date => {
  const [year, month, day] = dateStr.split('-').map(Number)
  return new Date(year, month - 1, day)
}
