/**
 * Pure rendering functions for the trajectory chart canvas.
 *
 * Each function draws a single visual layer onto the chart. They all take
 * a ChartLayout (computed once per frame) that holds the coordinate system,
 * data slice, and threshold values.
 */

import type { TrajectoryPoint } from '@/utils/trajectory'
import type { WorstWindow, DailyExpenseEntry } from '@/composables/useExpenseAnalysis'
import { CAUSE_COLORS } from '@/composables/useExpenseAnalysis'
import { PAYCHECK_INCOME_THRESHOLD } from '@/utils/constants'
import { formatDollars, shortDate, daysBetween } from '@/utils/format'

// ── Types ──────────────────────────────────────────────────────────────────

export interface ChartLayout {
  ctx: CanvasRenderingContext2D
  width: number
  height: number
  padding: { top: number; right: number; bottom: number; left: number }
  chartWidth: number
  chartHeight: number
  bottom: number
  xPos: (index: number) => number
  yPos: (value: number) => number
  slice: TrajectoryPoint[]
  viewStart: number
  minValue: number
  maxValue: number
  redThreshold: number
  yellowThreshold: number
  yRed: number
  yYellow: number
}

export interface HoverState {
  inWave: boolean
  sliceIdx: number | null
  mouseY: number
  mouseX: number
}

export interface HoveredBand {
  name: string
  amount: number
  color: string
}

/** Translated strings needed by pure canvas rendering functions. */
export interface ChartLabels {
  rangeDays: string    // e.g. "55 days" or "55일"
  today: string        // e.g. "today" or "오늘"
  dayOffset: string    // e.g. "+14d" or "+14일" — contains {count} placeholder
}

export interface ExpenseWaveOpts {
  worstWindow: WorstWindow | null
  expenseWave: number[]
  dailyExpenseStack: DailyExpenseEntry[][]
  masterExpenseOrder: string[]
  masterColorMap: Record<string, string>
}

export interface EventDotOpts {
  highlightDate?: string | null
  pulseDate?: string | null
  highlightedCause?: number | null
  worstWindow?: WorstWindow | null
  pulseElapsed?: number
}

// ── Layout ─────────────────────────────────────────────────────────────────

/** Compute pay-period expense thresholds for the visible slice. */
export function computeThresholds(slice: TrajectoryPoint[]): { red: number; yellow: number } {
  const payIndices: number[] = []
  for (let i = 0; i < slice.length; i++) {
    if (slice[i].events.some(event => event.amount > PAYCHECK_INCOME_THRESHOLD)) {
      payIndices.push(i)
    }
  }

  const windowStarts = [0, ...payIndices]
  let maxExpenses = 0

  for (let windowIdx = 0; windowIdx < windowStarts.length; windowIdx++) {
    const windowStart = windowStarts[windowIdx]
    const windowEnd = windowIdx + 1 < windowStarts.length
      ? windowStarts[windowIdx + 1] - 1
      : slice.length - 1
    let total = 0
    for (let i = windowStart; i <= windowEnd; i++) {
      for (const event of slice[i].events) {
        if (event.amount < 0) total += Math.abs(event.amount)
      }
    }
    if (total > maxExpenses) maxExpenses = total
  }

  const red = Math.round(maxExpenses)
  return { red, yellow: red + 1000 }
}

/** Set up the canvas and compute the drawing coordinate system.
 *
 *  @param backendLowestBalance - Optional intra-day low from the backend's
 *    expenses-before-income walk.  When provided, the y-axis range is
 *    extended so "risk wick" annotations are never clipped.
 */
export function buildLayout(
  canvas: HTMLCanvasElement,
  wrap: HTMLDivElement,
  data: TrajectoryPoint[],
  viewStart: number,
  viewCount: number,
  backendLowestBalance?: number | null,
): ChartLayout | null {
  const slice = data.slice(viewStart, viewStart + viewCount)
  if (!slice.length) return null

  const ctx = canvas.getContext('2d')
  if (!ctx) return null

  const rect = wrap.getBoundingClientRect()
  const pixelRatio = devicePixelRatio || 1
  canvas.width = rect.width * pixelRatio
  canvas.height = rect.height * pixelRatio
  canvas.style.width = `${rect.width}px`
  canvas.style.height = `${rect.height}px`
  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)

  const padding = { top: 28, right: 20, bottom: 38, left: 60 }
  const width = rect.width
  const height = rect.height
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom
  const { red: redThreshold, yellow: yellowThreshold } = computeThresholds(slice)
  // Include the intra-day low in the min so the risk wick is never clipped.
  let rawMin = Math.min(...slice.map(point => point.balance))
  if (backendLowestBalance != null && backendLowestBalance < rawMin) {
    rawMin = backendLowestBalance
  }
  const minValue = rawMin < 0 ? rawMin * 1.15 : 0
  const maxValue = Math.max(Math.max(...slice.map(point => point.balance)), yellowThreshold) * 1.1
  const xPos = (index: number) =>
    padding.left + (index / Math.max(slice.length - 1, 1)) * chartWidth
  const yPos = (value: number) =>
    padding.top + (1 - (value - minValue) / (maxValue - minValue)) * chartHeight
  const bottom = padding.top + chartHeight

  ctx.clearRect(0, 0, width, height)

  return {
    ctx, width, height, padding, chartWidth, chartHeight, bottom,
    xPos, yPos, slice, viewStart,
    minValue, maxValue, redThreshold, yellowThreshold,
    yRed: yPos(redThreshold),
    yYellow: yPos(yellowThreshold),
  }
}

/** Build the range label string for the current view. */
export function buildRangeLabel(slice: TrajectoryPoint[], labels: ChartLabels): string {
  const first = slice[0].date
  const last = slice[slice.length - 1].date
  return `${shortDate(first)} \u2192 ${shortDate(last)} \u00B7 ${labels.rangeDays}`
}

// ── Drawing functions ──────────────────────────────────────────────────────

/** Background zone bands (green safe / yellow tight / red danger). */
export function drawZoneBands(layout: ChartLayout): void {
  const { ctx, padding, chartWidth, yRed, yYellow, yellowThreshold, maxValue, bottom } = layout

  if (yellowThreshold < maxValue) {
    ctx.fillStyle = 'rgba(52,211,153,.02)'
    ctx.fillRect(padding.left, padding.top, chartWidth, yYellow - padding.top)
  }
  ctx.fillStyle = 'rgba(251,191,36,.02)'
  ctx.fillRect(padding.left, yYellow, chartWidth, yRed - yYellow)
  ctx.fillStyle = 'rgba(248,113,113,.02)'
  ctx.fillRect(padding.left, yRed, chartWidth, bottom - yRed)
}

/** Expense wave (stacked mountain when hovered, gradient fill otherwise). Returns hovered band info. */
export function drawExpenseWave(
  layout: ChartLayout,
  opts: ExpenseWaveOpts,
  hover: HoverState,
): HoveredBand | null {
  const { ctx, xPos, yRed, bottom, slice, viewStart, padding, chartWidth } = layout
  const { worstWindow, expenseWave, dailyExpenseStack, masterExpenseOrder, masterColorMap } = opts
  const maxExpenses = worstWindow ? worstWindow.totalExpenses : 0
  const waveHeight = bottom - yRed

  if (maxExpenses <= 0 || masterExpenseOrder.length <= 0) return null

  ctx.save()
  ctx.beginPath()
  ctx.rect(padding.left, yRed, chartWidth, waveHeight)
  ctx.clip()

  // Per-column stacks in master order for consistent band positions.
  const sliceStacks = slice.map((_, index) => {
    const globalIndex = viewStart + index
    const dayStack = dailyExpenseStack[globalIndex] || []
    return masterExpenseOrder.map(name => {
      const found = dayStack.find(entry => entry.name === name)
      return found ? found.amount : 0
    })
  })

  let hoveredBand: HoveredBand | null = null

  if (hover.inWave) {
    const hoveredBandIdx = findHoveredBand(
      hover, slice, sliceStacks, xPos, bottom, maxExpenses, waveHeight, masterExpenseOrder,
    )
    drawStackedMountain(
      ctx, slice, sliceStacks, xPos, bottom, maxExpenses, waveHeight,
      masterExpenseOrder, masterColorMap, hoveredBandIdx, hover,
    )

    // Subtle scan line at hover column.
    if (hover.sliceIdx !== null) {
      ctx.strokeStyle = 'rgba(255,255,255,.06)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(xPos(hover.sliceIdx), yRed)
      ctx.lineTo(xPos(hover.sliceIdx), bottom)
      ctx.stroke()
    }

    hoveredBand = hoveredBandIdx >= 0 ? {
      name: masterExpenseOrder[hoveredBandIdx],
      amount: sliceStacks[hover.sliceIdx!][hoveredBandIdx],
      color: masterColorMap[masterExpenseOrder[hoveredBandIdx]],
    } : null
  } else {
    drawDefaultWave(ctx, slice, xPos, viewStart, expenseWave, bottom, yRed, maxExpenses, waveHeight)
  }

  ctx.restore()
  return hoveredBand
}

/** Zone-colored fills under the trajectory line. */
export function drawTrajectoryFill(layout: ChartLayout): void {
  const { ctx, padding, chartWidth, xPos, yPos, bottom, slice, yRed, yYellow } = layout

  const zoneFill = (yTop: number, yBot: number, color: string) => {
    ctx.save()
    ctx.beginPath()
    ctx.rect(padding.left, yTop, chartWidth, yBot - yTop)
    ctx.clip()
    ctx.beginPath()
    ctx.moveTo(xPos(0), bottom)
    slice.forEach((_, index) => ctx.lineTo(xPos(index), yPos(slice[index].balance)))
    ctx.lineTo(xPos(slice.length - 1), bottom)
    ctx.closePath()
    ctx.fillStyle = color
    ctx.fill()
    ctx.restore()
  }

  zoneFill(padding.top, yYellow, 'rgba(52,211,153,.06)')
  zoneFill(yYellow, yRed, 'rgba(251,191,36,.06)')
}

/** Dashed threshold lines for red and yellow zones, plus a $0 baseline when the chart goes negative. */
export function drawThresholdLines(layout: ChartLayout): void {
  const { ctx, padding, chartWidth, yRed, yYellow, yPos, redThreshold, yellowThreshold, minValue, maxValue } = layout

  ctx.setLineDash([4, 6])
  if (redThreshold > minValue && redThreshold < maxValue) {
    ctx.strokeStyle = 'rgba(248,113,113,.25)'
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(padding.left, yRed); ctx.lineTo(padding.left + chartWidth, yRed); ctx.stroke()
  }
  if (yellowThreshold > minValue && yellowThreshold < maxValue) {
    ctx.strokeStyle = 'rgba(251,191,36,.18)'
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(padding.left, yYellow); ctx.lineTo(padding.left + chartWidth, yYellow); ctx.stroke()
  }

  // Draw a solid $0 baseline when the chart extends into negative territory.
  if (minValue < 0) {
    ctx.setLineDash([])
    ctx.strokeStyle = 'rgba(248,113,113,.45)'
    ctx.lineWidth = 1
    const yZero = yPos(0)
    ctx.beginPath(); ctx.moveTo(padding.left, yZero); ctx.lineTo(padding.left + chartWidth, yZero); ctx.stroke()
  }

  ctx.setLineDash([])
}

/** Grid lines and Y-axis dollar labels. */
export function drawGrid(layout: ChartLayout): void {
  const { ctx, padding, chartWidth, yPos, minValue, maxValue } = layout

  ctx.textAlign = 'right'
  for (let i = 0; i <= 5; i++) {
    const value = minValue + (maxValue - minValue) * (i / 5)
    const yCoord = yPos(value)
    ctx.strokeStyle = 'rgba(255,255,255,.015)'
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(padding.left, yCoord); ctx.lineTo(padding.left + chartWidth, yCoord); ctx.stroke()
    ctx.fillStyle = 'rgba(90,99,120,.5)'
    ctx.font = '10px IBM Plex Mono'
    ctx.fillText('$' + Math.round(value).toLocaleString(), padding.left - 7, yCoord + 3)
  }
  ctx.textAlign = 'left'
}

/** Main trajectory line with glow. */
export function drawTrajectoryLine(layout: ChartLayout): void {
  const { ctx, xPos, yPos, slice } = layout

  ctx.beginPath()
  slice.forEach((point, index) => {
    if (!index) ctx.moveTo(xPos(index), yPos(point.balance))
    else ctx.lineTo(xPos(index), yPos(point.balance))
  })
  ctx.strokeStyle = '#B8BEC9'
  ctx.lineWidth = 2
  ctx.lineJoin = 'round'
  ctx.stroke()

  // Glow.
  ctx.strokeStyle = 'rgba(184,190,201,.08)'
  ctx.lineWidth = 6
  ctx.beginPath()
  slice.forEach((point, index) => {
    if (!index) ctx.moveTo(xPos(index), yPos(point.balance))
    else ctx.lineTo(xPos(index), yPos(point.balance))
  })
  ctx.stroke()
}

/** Event dots with highlight, cause, and pulse effects. */
export function drawEventDots(layout: ChartLayout, opts: EventDotOpts): void {
  const { ctx, xPos, yPos, slice } = layout
  const { highlightDate, pulseDate, highlightedCause, worstWindow, pulseElapsed } = opts
  const PULSE_DURATION = 2500

  slice.forEach((point, index) => {
    if (!point.events.length) return
    const dotX = xPos(index)
    const dotY = yPos(point.balance)
    const hasIncome = point.events.some(event => event.amount > 0)
    const isRent = point.events.some(event => event.name.toLowerCase().includes('rent') && event.amount < -500)
    let dotColor = 'rgba(184,190,201,.4)'
    let dotRadius = 3
    if (hasIncome) { dotColor = '#A78BFA'; dotRadius = 5 }
    if (isRent) { dotColor = '#FBBF24'; dotRadius = 5 }

    // Highlight cause from CausePanel hover.
    if (highlightedCause !== null && highlightedCause !== undefined
      && worstWindow && worstWindow.expenses[highlightedCause]) {
      const causeName = worstWindow.expenses[highlightedCause].name
      if (point.events.some(event => event.name === causeName)
        && point.date >= worstWindow.startDate && point.date <= worstWindow.endDate) {
        dotColor = CAUSE_COLORS[highlightedCause % CAUSE_COLORS.length]
        dotRadius = 8
        const [colorRed, colorGreen, colorBlue] = hexToRgb(dotColor)
        ctx.beginPath(); ctx.arc(dotX, dotY, 14, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${colorRed},${colorGreen},${colorBlue},.1)`
        ctx.fill()
      }
    }

    // Highlight from event list hover.
    if (highlightDate && point.date === highlightDate) {
      dotColor = '#E8ECF2'; dotRadius = 8
      ctx.beginPath(); ctx.arc(dotX, dotY, 14, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(232,236,242,.07)'; ctx.fill()
    }

    // Pulse animation from event click.
    if (pulseDate && point.date === pulseDate && pulseElapsed !== undefined) {
      const progress = pulseElapsed / PULSE_DURATION
      const wave1 = (pulseElapsed % 800) / 800
      const wave2 = ((pulseElapsed + 400) % 800) / 800
      const fadeOut = 1 - progress

      for (const waveProgress of [wave1, wave2]) {
        const ringRadius = 8 + waveProgress * 20
        const alpha = (1 - waveProgress) * 0.35 * fadeOut
        ctx.beginPath(); ctx.arc(dotX, dotY, ringRadius, 0, Math.PI * 2)
        ctx.strokeStyle = `rgba(167,139,250,${alpha})`
        ctx.lineWidth = 2
        ctx.stroke()
      }

      dotColor = '#A78BFA'; dotRadius = 6
      ctx.beginPath(); ctx.arc(dotX, dotY, 10, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(167,139,250,${0.12 * (1 - progress)})`; ctx.fill()
    }

    ctx.beginPath(); ctx.arc(dotX, dotY, dotRadius, 0, Math.PI * 2)
    ctx.fillStyle = dotColor; ctx.fill()
  })
}

/** Lowest point marker with pill label.
 *
 *  When backend lowest values are provided, the annotation shows the
 *  backend's expenses-before-income intra-day lowest at the matching
 *  date.  If the intra-day low is below the end-of-day balance (i.e.
 *  income arrived later that day), a dashed "risk wick" connects the
 *  trajectory line point down to the annotation — like a candlestick
 *  wick on a stock chart.
 */
export function drawLowestPoint(
  layout: ChartLayout,
  backendLowestBalance: number | null,
  backendLowestDate: string | null,
): void {
  const { ctx, xPos, yPos, slice } = layout

  // Find the index to place the annotation.  If the backend provides
  // a lowest date, find the closest trajectory point.  Otherwise fall
  // back to the minimum end-of-day balance in the visible slice.
  let lowestIndex: number
  let intradayLow: number | null = null

  if (backendLowestBalance != null && backendLowestDate) {
    // Find the trajectory point at or nearest the backend's date.
    lowestIndex = 0
    let bestDist = Infinity
    for (let i = 0; i < slice.length; i++) {
      if (slice[i].date === backendLowestDate) { lowestIndex = i; break }
      const dist = Math.abs(new Date(slice[i].date).getTime() - new Date(backendLowestDate).getTime())
      if (dist < bestDist) { bestDist = dist; lowestIndex = i }
    }
    intradayLow = backendLowestBalance
  } else {
    lowestIndex = slice.reduce(
      (minIdx, point, idx) => point.balance < slice[minIdx].balance ? idx : minIdx, 0,
    )
  }

  // End-of-day balance at this date (where the trajectory line is).
  const lineBalance = slice[lowestIndex].balance
  // The displayed value: intra-day low if available, otherwise line balance.
  const displayBalance = intradayLow ?? lineBalance
  // Whether there's a gap between the line and the intra-day dip.
  const hasWick = intradayLow != null && intradayLow < lineBalance

  const lowestX = xPos(lowestIndex)
  const lineY = yPos(lineBalance)
  // Annotation sits at the intra-day low (wick tip) or on the line.
  const annotationY = hasWick ? yPos(intradayLow!) : lineY

  // ── Risk wick: dashed line from the trajectory point to intra-day low ──
  if (hasWick) {
    ctx.save()
    ctx.setLineDash([4, 3])
    ctx.beginPath()
    ctx.moveTo(lowestX, lineY)
    ctx.lineTo(lowestX, annotationY)
    ctx.strokeStyle = 'rgba(248,113,113,.45)'
    ctx.lineWidth = 1.5
    ctx.stroke()
    ctx.setLineDash([])
    ctx.restore()

    // Small anchor dot on the trajectory line.
    ctx.beginPath(); ctx.arc(lowestX, lineY, 3, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(248,113,113,.5)'; ctx.fill()
  }

  // Circle markers at the annotation point (wick tip or line).
  ctx.beginPath(); ctx.arc(lowestX, annotationY, 12, 0, Math.PI * 2)
  ctx.strokeStyle = 'rgba(248,113,113,.25)'; ctx.lineWidth = 1.5; ctx.stroke()
  ctx.beginPath(); ctx.arc(lowestX, annotationY, 4, 0, Math.PI * 2)
  ctx.fillStyle = '#F87171'; ctx.fill()

  // Pill background.
  const lowText = (displayBalance < 0 ? '-' : '') + formatDollars(displayBalance)
  ctx.font = '700 13px IBM Plex Mono'
  const lowTextWidth = ctx.measureText(lowText).width
  ctx.font = '600 9px Sora'
  const lowLabelWidth = ctx.measureText('LOWEST').width
  const pillContentWidth = Math.max(lowTextWidth, lowLabelWidth)
  const pillWidth = pillContentWidth + 16
  const pillHeight = 32
  ctx.fillStyle = 'rgba(6,8,12,.85)'
  ctx.fillRect(lowestX - pillWidth / 2, annotationY - 18 - pillHeight, pillWidth, pillHeight)
  ctx.strokeStyle = 'rgba(248,113,113,.2)'
  ctx.lineWidth = 1
  ctx.strokeRect(lowestX - pillWidth / 2, annotationY - 18 - pillHeight, pillWidth, pillHeight)
  ctx.fillStyle = '#F87171'
  ctx.textAlign = 'center'
  ctx.font = '700 13px IBM Plex Mono'
  ctx.fillText(lowText, lowestX, annotationY - 22)
  ctx.font = '600 9px Sora'
  ctx.fillText('LOWEST', lowestX, annotationY - 36)
  ctx.textAlign = 'left'
}

/** X-axis date labels with day offsets. */
export function drawXAxis(layout: ChartLayout, firstDate: string, labels: ChartLabels): void {
  const { ctx, xPos, bottom, slice } = layout

  ctx.textAlign = 'center'
  const step = slice.length > 60 ? 7 : slice.length > 30 ? 4 : slice.length > 15 ? 2 : 1
  slice.forEach((point, index) => {
    if (index % step && index !== slice.length - 1 && index !== 0) return
    const labelX = xPos(index)
    ctx.fillStyle = 'rgba(90,99,120,.4)'
    ctx.font = '9px Sora'
    ctx.fillText(shortDate(point.date), labelX, bottom + 14)
    const days = daysBetween(firstDate, point.date)
    ctx.fillStyle = 'rgba(90,99,120,.22)'
    ctx.font = '8px IBM Plex Mono'
    ctx.fillText(days === 0 ? labels.today : labels.dayOffset.replace('{count}', String(days)), labelX, bottom + 25)
  })
  ctx.textAlign = 'left'
}

// ── Private helpers ────────────────────────────────────────────────────────

function hexToRgb(hex: string): [number, number, number] {
  return [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ]
}

/** Find which expense band the cursor is over via interpolation between columns. */
function findHoveredBand(
  hover: HoverState,
  slice: TrajectoryPoint[],
  sliceStacks: number[][],
  xPos: (index: number) => number,
  bottom: number,
  maxExpenses: number,
  waveHeight: number,
  masterOrder: string[],
): number {
  if (hover.sliceIdx === null || hover.sliceIdx < 0 || hover.sliceIdx >= slice.length) return -1

  let leftIndex = hover.sliceIdx
  let rightIndex = hover.sliceIdx
  let frac = 0

  if (hover.sliceIdx > 0 && hover.mouseX < xPos(hover.sliceIdx)) {
    leftIndex = hover.sliceIdx - 1
    rightIndex = hover.sliceIdx
    const span = xPos(rightIndex) - xPos(leftIndex)
    frac = span > 0 ? (hover.mouseX - xPos(leftIndex)) / span : 0
  } else if (hover.sliceIdx < slice.length - 1 && hover.mouseX > xPos(hover.sliceIdx)) {
    leftIndex = hover.sliceIdx
    rightIndex = hover.sliceIdx + 1
    const span = xPos(rightIndex) - xPos(leftIndex)
    frac = span > 0 ? (hover.mouseX - xPos(leftIndex)) / span : 0
  }

  let cumulativePixel = bottom
  for (let j = 0; j < masterOrder.length; j++) {
    const amountLeft = sliceStacks[leftIndex]?.[j] ?? 0
    const amountRight = sliceStacks[rightIndex]?.[j] ?? 0
    const amount = amountLeft + (amountRight - amountLeft) * frac
    const bandHeight = (amount / maxExpenses) * waveHeight
    const topPixel = cumulativePixel - bandHeight
    if (hover.mouseY >= topPixel && hover.mouseY <= cumulativePixel && amount > 0.5) return j
    cumulativePixel = topPixel
  }

  return -1
}

/** Draw the colored stacked mountain when hovering the expense wave. */
function drawStackedMountain(
  ctx: CanvasRenderingContext2D,
  slice: TrajectoryPoint[],
  sliceStacks: number[][],
  xPos: (index: number) => number,
  bottom: number,
  maxExpenses: number,
  waveHeight: number,
  masterOrder: string[],
  colorMap: Record<string, string>,
  hoveredBandIdx: number,
  hover: HoverState,
): void {
  masterOrder.forEach((expName, expenseIndex) => {
    const color = colorMap[expName] ?? CAUSE_COLORS[expenseIndex % CAUSE_COLORS.length]
    const [colorRed, colorGreen, colorBlue] = hexToRgb(color)
    const isHovered = expenseIndex === hoveredBandIdx
    const hasAmount = sliceStacks.some(stack => stack[expenseIndex] > 0)
    if (!hasAmount) return

    function bandTop(sliceIndex: number) {
      let sum = 0
      for (let j = 0; j <= expenseIndex; j++) sum += sliceStacks[sliceIndex][j]
      return bottom - (sum / maxExpenses) * waveHeight
    }
    function bandBottom(sliceIndex: number) {
      let sum = 0
      for (let j = 0; j < expenseIndex; j++) sum += sliceStacks[sliceIndex][j]
      return bottom - (sum / maxExpenses) * waveHeight
    }

    // Band fill.
    ctx.beginPath()
    ctx.moveTo(xPos(0), bandTop(0))
    for (let i = 1; i < slice.length; i++) ctx.lineTo(xPos(i), bandTop(i))
    for (let i = slice.length - 1; i >= 0; i--) ctx.lineTo(xPos(i), bandBottom(i))
    ctx.closePath()
    ctx.fillStyle = `rgba(${colorRed},${colorGreen},${colorBlue},${isHovered ? '.28' : '.1'})`
    ctx.fill()

    // Stroke only where band has height.
    ctx.beginPath()
    let inBand = false
    for (let i = 0; i < slice.length; i++) {
      if (sliceStacks[i][expenseIndex] > 0) {
        if (!inBand) { ctx.moveTo(xPos(i), bandTop(i)); inBand = true }
        else ctx.lineTo(xPos(i), bandTop(i))
      } else {
        inBand = false
      }
    }
    ctx.strokeStyle = `rgba(${colorRed},${colorGreen},${colorBlue},${isHovered ? '.6' : '.15'})`
    ctx.lineWidth = isHovered ? 1.5 : 0.5
    ctx.stroke()

    // Label the hovered band at the cursor column.
    if (isHovered && hover.sliceIdx !== null) {
      const midY = (bandTop(hover.sliceIdx) + bandBottom(hover.sliceIdx)) / 2
      ctx.fillStyle = `rgba(${colorRed},${colorGreen},${colorBlue},.9)`
      ctx.font = '600 9px Sora'
      ctx.textAlign = 'center'
      ctx.fillText(expName, xPos(hover.sliceIdx), midY + 3)
      ctx.textAlign = 'left'
    }
  })
}

/** Draw the default red gradient wave when not hovering. */
function drawDefaultWave(
  ctx: CanvasRenderingContext2D,
  slice: TrajectoryPoint[],
  xPos: (index: number) => number,
  viewStart: number,
  expenseWave: number[],
  bottom: number,
  yRed: number,
  maxExpenses: number,
  waveHeight: number,
): void {
  ctx.beginPath()
  ctx.moveTo(xPos(0), bottom)
  slice.forEach((_, index) => {
    const globalIndex = viewStart + index
    const cumulativeExpense = expenseWave[globalIndex] || 0
    ctx.lineTo(xPos(index), bottom - (cumulativeExpense / maxExpenses) * waveHeight)
  })
  ctx.lineTo(xPos(slice.length - 1), bottom)
  ctx.closePath()
  const grad = ctx.createLinearGradient(0, yRed, 0, bottom)
  grad.addColorStop(0, 'rgba(248,113,113,.12)')
  grad.addColorStop(0.5, 'rgba(248,113,113,.06)')
  grad.addColorStop(1, 'rgba(248,113,113,.01)')
  ctx.fillStyle = grad
  ctx.fill()
  ctx.beginPath()
  slice.forEach((_, index) => {
    const globalIndex = viewStart + index
    const cumulativeExpense = expenseWave[globalIndex] || 0
    const waveY = bottom - (cumulativeExpense / maxExpenses) * waveHeight
    if (!index) ctx.moveTo(xPos(index), waveY)
    else ctx.lineTo(xPos(index), waveY)
  })
  ctx.strokeStyle = 'rgba(248,113,113,.2)'
  ctx.lineWidth = 1.5
  ctx.lineJoin = 'round'
  ctx.stroke()
}
