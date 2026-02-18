<template>
  <div>
    <div class="sh">
      <span class="sh-t">Balance Trajectory</span>
      <span class="sh-m">{{ rangeLabel }}</span>
    </div>
    <InfoBar :data="infoBarData" />
    <div
      class="chart-box"
      ref="wrapRef"
      :class="{ grabbing: isDragging }"
      @mousedown="onMouseDown"
      @mousemove="onMouseMove"
      @mouseleave="onMouseLeave"
      @wheel.prevent="onWheel"
      @touchstart="onTouchStart"
      @touchmove.prevent="onTouchMove"
      @touchend="onTouchEnd"
    >
      <canvas ref="canvasRef" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import type { TrajectoryPoint } from '@/composables/useDashboard'
import type { WorstWindow, DailyExpenseEntry } from '@/composables/useExpenseAnalysis'
import type { InfoBarData } from '@/components/InfoBar.vue'
import InfoBar from '@/components/InfoBar.vue'
import { parseLocalDate } from '@/utils/format'
import { CAUSE_COLORS } from '@/composables/useExpenseAnalysis'

const props = defineProps<{
  data: TrajectoryPoint[]
  highlightDate?: string | null
  pulseDate?: string | null
  highlightedCause?: number | null
  worstWindow?: WorstWindow | null
  expenseWave?: number[]
  dailyExpenseStack?: DailyExpenseEntry[][]
  masterExpenseOrder?: string[]
  masterColorMap?: Record<string, string>
}>()

const emit = defineEmits<{
  infoUpdate: [data: InfoBarData | null]
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const wrapRef = ref<HTMLDivElement | null>(null)
const isDragging = ref(false)
const rangeLabel = ref('')
const infoBarData = ref<InfoBarData | null>(null)

// Windowed view state.
let viewStart = 0
let viewCount = 30

// Hover state for expense wave.
let hoverInWave = false
let hoverSliceIdx: number | null = null
let hoverMouseY = 0
let hoverMouseX = 0

const fmtShort = (n: number) =>
  '$' + Math.abs(Math.round(n)).toLocaleString()

const shortDate = (d: string) =>
  parseLocalDate(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

const daysBetween = (a: string, b: string) =>
  Math.round((parseLocalDate(b).getTime() - parseLocalDate(a).getTime()) / 864e5)

// Pulse animation state.
let pulseStartTime = 0
let pulseAnimId = 0
const PULSE_DURATION = 2500

function startPulse() {
  cancelAnimationFrame(pulseAnimId)
  pulseStartTime = performance.now()
  const tick = () => {
    const elapsed = performance.now() - pulseStartTime
    if (elapsed > PULSE_DURATION) {
      draw()
      return
    }
    draw(elapsed)
    pulseAnimId = requestAnimationFrame(tick)
  }
  pulseAnimId = requestAnimationFrame(tick)
}

// Store chart mapping for hover hit-testing.
let chartState: {
  xPos: (i: number) => number
  yPos: (v: number) => number
  slice: TrajectoryPoint[]
  redT: number
  yellowT: number
} | null = null

// Store hovered band info from last draw for info bar.
let lastHoveredBand: { name: string; amount: number; color: string } | null = null

function clampView() {
  if (viewStart < 0) viewStart = 0
  if (viewStart > props.data.length - viewCount) viewStart = props.data.length - viewCount
  if (viewStart < 0) viewStart = 0
}

/** Compute threshold for a visible slice.
 *  Splits the window into pay periods, sums expenses in each, and takes the
 *  max as the "high water mark". Yellow = red + 1000. */
function computeWindowThreshold(slice: TrajectoryPoint[]): { red: number; yellow: number } {
  const payIndices: number[] = []
  for (let i = 0; i < slice.length; i++) {
    if (slice[i].events.some(e => e.amount > 500)) payIndices.push(i)
  }

  const windowStarts = [0, ...payIndices]
  let maxExpenses = 0

  for (let w = 0; w < windowStarts.length; w++) {
    const wStart = windowStarts[w]
    const wEnd = w + 1 < windowStarts.length ? windowStarts[w + 1] - 1 : slice.length - 1
    let total = 0
    for (let i = wStart; i <= wEnd; i++) {
      for (const ev of slice[i].events) {
        if (ev.amount < 0) total += Math.abs(ev.amount)
      }
    }
    if (total > maxExpenses) maxExpenses = total
  }

  const red = Math.round(maxExpenses)
  return { red, yellow: red + 1000 }
}

function draw(pulseElapsed?: number) {
  const canvas = canvasRef.value
  const wrap = wrapRef.value
  if (!canvas || !wrap || !props.data.length) return

  const ctx = canvas.getContext('2d')!
  clampView()
  const slice = props.data.slice(viewStart, viewStart + viewCount)
  if (!slice.length) return

  const rect = wrap.getBoundingClientRect()
  const dpr = devicePixelRatio || 1
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  canvas.style.width = `${rect.width}px`
  canvas.style.height = `${rect.height}px`
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  const P = { top: 28, right: 20, bottom: 38, left: 60 }
  const W = rect.width
  const H = rect.height
  const cW = W - P.left - P.right
  const cH = H - P.top - P.bottom
  const { red: redT, yellow: yellowT } = computeWindowThreshold(slice)
  const mn = 0
  const mx = Math.max(Math.max(...slice.map(t => t.balance)), yellowT) * 1.1
  const xPos = (i: number) => P.left + (i / Math.max(slice.length - 1, 1)) * cW
  const yPos = (v: number) => P.top + (1 - (v - mn) / (mx - mn)) * cH
  const chartBottom = P.top + cH

  chartState = { xPos, yPos, slice, redT, yellowT }
  const calDays = daysBetween(slice[0].date, slice[slice.length - 1].date)
  rangeLabel.value = `${shortDate(slice[0].date)} \u2192 ${shortDate(slice[slice.length - 1].date)} \u00B7 ${calDays} days`

  ctx.clearRect(0, 0, W, H)

  const yRed = yPos(redT)
  const yYellow = yPos(yellowT)

  // Zone background bands.
  if (yellowT < mx) {
    ctx.fillStyle = 'rgba(52,211,153,.02)'
    ctx.fillRect(P.left, P.top, cW, yYellow - P.top)
  }
  ctx.fillStyle = 'rgba(251,191,36,.02)'
  ctx.fillRect(P.left, yYellow, cW, yRed - yYellow)

  // ── Expense wave below the threshold ──
  const ww = props.worstWindow
  const maxExp = ww ? ww.totalExpenses : 0
  const waveH = chartBottom - yRed

  ctx.fillStyle = 'rgba(248,113,113,.02)'
  ctx.fillRect(P.left, yRed, cW, waveH)

  const expWave = props.expenseWave ?? []
  const dailyStack = props.dailyExpenseStack ?? []
  const masterOrder = props.masterExpenseOrder ?? []
  const colorMap = props.masterColorMap ?? {}

  if (maxExp > 0 && masterOrder.length > 0) {
    ctx.save()
    ctx.beginPath()
    ctx.rect(P.left, yRed, cW, waveH)
    ctx.clip()

    // Per-column stacks in master order for consistent band positions.
    const sliceStacks = slice.map((_, i) => {
      const gi = viewStart + i
      const dayStack = dailyStack[gi] || []
      return masterOrder.map(name => {
        const found = dayStack.find(e => e.name === name)
        return found ? found.amount : 0
      })
    })

    // Determine which band the mouse is over via interpolation.
    let hoveredBandIdx = -1
    if (hoverInWave && hoverSliceIdx !== null && hoverSliceIdx >= 0 && hoverSliceIdx < slice.length && hoverMouseX !== undefined) {
      let li = hoverSliceIdx
      let ri = hoverSliceIdx
      let frac = 0

      if (hoverSliceIdx > 0 && hoverMouseX < xPos(hoverSliceIdx)) {
        li = hoverSliceIdx - 1
        ri = hoverSliceIdx
        const span = xPos(ri) - xPos(li)
        frac = span > 0 ? (hoverMouseX - xPos(li)) / span : 0
      } else if (hoverSliceIdx < slice.length - 1 && hoverMouseX > xPos(hoverSliceIdx)) {
        li = hoverSliceIdx
        ri = hoverSliceIdx + 1
        const span = xPos(ri) - xPos(li)
        frac = span > 0 ? (hoverMouseX - xPos(li)) / span : 0
      }

      let cumPx = chartBottom
      for (let j = 0; j < masterOrder.length; j++) {
        const amtL = sliceStacks[li]?.[j] ?? 0
        const amtR = sliceStacks[ri]?.[j] ?? 0
        const amt = amtL + (amtR - amtL) * frac
        const bandH = (amt / maxExp) * waveH
        const topPx = cumPx - bandH
        if (hoverMouseY >= topPx && hoverMouseY <= cumPx && amt > 0.5) {
          hoveredBandIdx = j
          break
        }
        cumPx = topPx
      }
    }

    if (hoverInWave) {
      // ── Stacked colored mountain ──
      masterOrder.forEach((expName, ei) => {
        const color = colorMap[expName] ?? CAUSE_COLORS[ei % CAUSE_COLORS.length]
        const cr = parseInt(color.slice(1, 3), 16)
        const cg = parseInt(color.slice(3, 5), 16)
        const cb = parseInt(color.slice(5, 7), 16)
        const isHovered = ei === hoveredBandIdx
        const hasAmount = sliceStacks.some(ss => ss[ei] > 0)
        if (!hasAmount) return

        function bandTop(si: number) {
          let s = 0
          for (let j = 0; j <= ei; j++) s += sliceStacks[si][j]
          return chartBottom - (s / maxExp) * waveH
        }
        function bandBot(si: number) {
          let s = 0
          for (let j = 0; j < ei; j++) s += sliceStacks[si][j]
          return chartBottom - (s / maxExp) * waveH
        }

        // Full-width band fill (zero-height segments are naturally invisible).
        ctx.beginPath()
        ctx.moveTo(xPos(0), bandTop(0))
        for (let i = 1; i < slice.length; i++) ctx.lineTo(xPos(i), bandTop(i))
        for (let i = slice.length - 1; i >= 0; i--) ctx.lineTo(xPos(i), bandBot(i))
        ctx.closePath()
        ctx.fillStyle = `rgba(${cr},${cg},${cb},${isHovered ? '.28' : '.1'})`
        ctx.fill()

        // Stroke only where band has height to avoid zero-height edge artifacts.
        ctx.beginPath()
        let inBand = false
        for (let i = 0; i < slice.length; i++) {
          if (sliceStacks[i][ei] > 0) {
            if (!inBand) { ctx.moveTo(xPos(i), bandTop(i)); inBand = true }
            else ctx.lineTo(xPos(i), bandTop(i))
          } else {
            inBand = false
          }
        }
        ctx.strokeStyle = `rgba(${cr},${cg},${cb},${isHovered ? '.6' : '.15'})`
        ctx.lineWidth = isHovered ? 1.5 : 0.5
        ctx.stroke()

        // Label the hovered band at the cursor column.
        if (isHovered && hoverSliceIdx !== null) {
          const midY = (bandTop(hoverSliceIdx) + bandBot(hoverSliceIdx)) / 2
          ctx.fillStyle = `rgba(${cr},${cg},${cb},.9)`
          ctx.font = '600 9px Sora'
          ctx.textAlign = 'center'
          ctx.fillText(expName, xPos(hoverSliceIdx), midY + 3)
          ctx.textAlign = 'left'
        }
      })

      // Subtle scan line at hover column.
      if (hoverSliceIdx !== null) {
        ctx.strokeStyle = 'rgba(255,255,255,.06)'
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(xPos(hoverSliceIdx), yRed)
        ctx.lineTo(xPos(hoverSliceIdx), chartBottom)
        ctx.stroke()
      }

      // Store hovered band for info bar.
      lastHoveredBand = hoveredBandIdx >= 0 ? {
        name: masterOrder[hoveredBandIdx],
        amount: sliceStacks[hoverSliceIdx!][hoveredBandIdx],
        color: colorMap[masterOrder[hoveredBandIdx]],
      } : null
    } else {
      // ── Default red gradient wave ──
      lastHoveredBand = null
      ctx.beginPath()
      ctx.moveTo(xPos(0), chartBottom)
      slice.forEach((_, i) => {
        const gi = viewStart + i
        const cum = expWave[gi] || 0
        ctx.lineTo(xPos(i), chartBottom - (cum / maxExp) * waveH)
      })
      ctx.lineTo(xPos(slice.length - 1), chartBottom)
      ctx.closePath()
      const grad = ctx.createLinearGradient(0, yRed, 0, chartBottom)
      grad.addColorStop(0, 'rgba(248,113,113,.12)')
      grad.addColorStop(0.5, 'rgba(248,113,113,.06)')
      grad.addColorStop(1, 'rgba(248,113,113,.01)')
      ctx.fillStyle = grad
      ctx.fill()
      ctx.beginPath()
      slice.forEach((_, i) => {
        const gi = viewStart + i
        const cum = expWave[gi] || 0
        const wy = chartBottom - (cum / maxExp) * waveH
        if (!i) ctx.moveTo(xPos(i), wy)
        else ctx.lineTo(xPos(i), wy)
      })
      ctx.strokeStyle = 'rgba(248,113,113,.2)'
      ctx.lineWidth = 1.5
      ctx.lineJoin = 'round'
      ctx.stroke()
    }

    ctx.restore()
  }

  // Trajectory fill colored by zone.
  const zoneFill = (yTop: number, yBot: number, color: string) => {
    ctx.save()
    ctx.beginPath()
    ctx.rect(P.left, yTop, cW, yBot - yTop)
    ctx.clip()
    ctx.beginPath()
    ctx.moveTo(xPos(0), chartBottom)
    slice.forEach((_, i) => ctx.lineTo(xPos(i), yPos(slice[i].balance)))
    ctx.lineTo(xPos(slice.length - 1), chartBottom)
    ctx.closePath()
    ctx.fillStyle = color
    ctx.fill()
    ctx.restore()
  }
  zoneFill(P.top, yYellow, 'rgba(52,211,153,.06)')
  zoneFill(yYellow, yRed, 'rgba(251,191,36,.06)')

  // Threshold dashed lines (no text labels -- info bar replaces them).
  ctx.setLineDash([4, 6])
  if (redT > mn && redT < mx) {
    ctx.strokeStyle = 'rgba(248,113,113,.25)'
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(P.left, yRed); ctx.lineTo(P.left + cW, yRed); ctx.stroke()
  }
  if (yellowT > mn && yellowT < mx) {
    ctx.strokeStyle = 'rgba(251,191,36,.18)'
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(P.left, yYellow); ctx.lineTo(P.left + cW, yYellow); ctx.stroke()
  }
  ctx.setLineDash([])

  // Grid lines.
  ctx.textAlign = 'right'
  for (let i = 0; i <= 5; i++) {
    const v = mn + (mx - mn) * (i / 5)
    const y = yPos(v)
    ctx.strokeStyle = 'rgba(255,255,255,.015)'
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(P.left, y); ctx.lineTo(P.left + cW, y); ctx.stroke()
    ctx.fillStyle = 'rgba(90,99,120,.5)'
    ctx.font = '10px IBM Plex Mono'
    ctx.fillText('$' + Math.round(v).toLocaleString(), P.left - 7, y + 3)
  }
  ctx.textAlign = 'left'

  // Trajectory line.
  ctx.beginPath()
  slice.forEach((t, i) => {
    if (!i) ctx.moveTo(xPos(i), yPos(t.balance))
    else ctx.lineTo(xPos(i), yPos(t.balance))
  })
  ctx.strokeStyle = '#B8BEC9'
  ctx.lineWidth = 2
  ctx.lineJoin = 'round'
  ctx.stroke()

  // Glow.
  ctx.strokeStyle = 'rgba(184,190,201,.08)'
  ctx.lineWidth = 6
  ctx.beginPath()
  slice.forEach((t, i) => {
    if (!i) ctx.moveTo(xPos(i), yPos(t.balance))
    else ctx.lineTo(xPos(i), yPos(t.balance))
  })
  ctx.stroke()

  // Event dots.
  const lowI = slice.reduce((m, t, i) => t.balance < slice[m].balance ? i : m, 0)
  slice.forEach((t, i) => {
    if (!t.events.length) return
    const x = xPos(i)
    const y = yPos(t.balance)
    const inc = t.events.some(e => e.amount > 0)
    const isRent = t.events.some(e => e.name.toLowerCase().includes('rent') && e.amount < -500)
    let c = 'rgba(184,190,201,.4)'
    let r = 3
    if (inc) { c = '#A78BFA'; r = 5 }
    if (isRent) { c = '#FBBF24'; r = 5 }

    // Highlight cause from CausePanel hover (scoped to worst window).
    if (props.highlightedCause !== null && props.highlightedCause !== undefined && ww && ww.expenses[props.highlightedCause]) {
      const causeName = ww.expenses[props.highlightedCause].name
      if (t.events.some(e => e.name === causeName) && t.date >= ww.startDate && t.date <= ww.endDate) {
        c = CAUSE_COLORS[props.highlightedCause % CAUSE_COLORS.length]
        r = 8
        const cc = c
        const ccr = parseInt(cc.slice(1, 3), 16)
        const ccg = parseInt(cc.slice(3, 5), 16)
        const ccb = parseInt(cc.slice(5, 7), 16)
        ctx.beginPath(); ctx.arc(x, y, 14, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(${ccr},${ccg},${ccb},.1)`
        ctx.fill()
      }
    }

    // Highlight from event list hover.
    if (props.highlightDate && t.date === props.highlightDate) {
      c = '#E8ECF2'; r = 8
      ctx.beginPath(); ctx.arc(x, y, 14, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(232,236,242,.07)'; ctx.fill()
    }

    // Pulse animation from event click.
    if (props.pulseDate && t.date === props.pulseDate && pulseElapsed !== undefined) {
      const progress = pulseElapsed / PULSE_DURATION
      const wave1 = (pulseElapsed % 800) / 800
      const wave2 = ((pulseElapsed + 400) % 800) / 800
      const fadeOut = 1 - progress

      for (const w of [wave1, wave2]) {
        const ringR = 8 + w * 20
        const alpha = (1 - w) * 0.35 * fadeOut
        ctx.beginPath(); ctx.arc(x, y, ringR, 0, Math.PI * 2)
        ctx.strokeStyle = `rgba(167,139,250,${alpha})`
        ctx.lineWidth = 2
        ctx.stroke()
      }

      c = '#A78BFA'; r = 6
      ctx.beginPath(); ctx.arc(x, y, 10, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(167,139,250,${0.12 * (1 - progress)})`; ctx.fill()
    }

    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fillStyle = c; ctx.fill()
  })

  // Lowest point marker -- sharp pill.
  const lx = xPos(lowI)
  const ly = yPos(slice[lowI].balance)
  ctx.beginPath(); ctx.arc(lx, ly, 12, 0, Math.PI * 2)
  ctx.strokeStyle = 'rgba(248,113,113,.25)'; ctx.lineWidth = 1.5; ctx.stroke()
  ctx.beginPath(); ctx.arc(lx, ly, 4, 0, Math.PI * 2)
  ctx.fillStyle = '#F87171'; ctx.fill()

  // Pill background for readability.
  const lowText = fmtShort(slice[lowI].balance)
  ctx.font = '700 13px IBM Plex Mono'
  const lowTW = ctx.measureText(lowText).width
  ctx.font = '600 9px Sora'
  const lowLabelW = ctx.measureText('LOWEST').width
  const pillContentW = Math.max(lowTW, lowLabelW)
  const pillW = pillContentW + 16
  const pillH = 32
  ctx.fillStyle = 'rgba(6,8,12,.85)'
  ctx.fillRect(lx - pillW / 2, ly - 18 - pillH, pillW, pillH)
  ctx.strokeStyle = 'rgba(248,113,113,.2)'
  ctx.lineWidth = 1
  ctx.strokeRect(lx - pillW / 2, ly - 18 - pillH, pillW, pillH)
  ctx.fillStyle = '#F87171'
  ctx.textAlign = 'center'
  ctx.font = '700 13px IBM Plex Mono'
  ctx.fillText(lowText, lx, ly - 22)
  ctx.font = '600 9px Sora'
  ctx.fillText('LOWEST', lx, ly - 36)
  ctx.textAlign = 'left'

  // X-axis labels.
  ctx.textAlign = 'center'
  const step = slice.length > 60 ? 7 : slice.length > 30 ? 4 : slice.length > 15 ? 2 : 1
  slice.forEach((t, i) => {
    if (i % step && i !== slice.length - 1 && i !== 0) return
    const x = xPos(i)
    ctx.fillStyle = 'rgba(90,99,120,.4)'
    ctx.font = '9px Sora'
    ctx.fillText(shortDate(t.date), x, chartBottom + 14)
    const days = daysBetween(props.data[0].date, t.date)
    ctx.fillStyle = 'rgba(90,99,120,.22)'
    ctx.font = '8px IBM Plex Mono'
    ctx.fillText(days === 0 ? 'today' : `+${days}d`, x, chartBottom + 25)
  })
  ctx.textAlign = 'left'
}

// ── Info bar update on hover ──
function updateInfoBar(clientX: number, clientY: number) {
  if (!chartState || !wrapRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const mx = clientX - rect.left
  const my = clientY - rect.top
  const { xPos, yPos, slice, redT, yellowT } = chartState

  let ci = 0
  let cd = Infinity
  slice.forEach((_, i) => {
    const d = Math.abs(xPos(i) - mx)
    if (d < cd) { cd = d; ci = i }
  })

  if (cd > 25) {
    infoBarData.value = null
    hoverInWave = false
    hoverSliceIdx = null
    draw()
    return
  }

  const t = slice[ci]
  const yRedPos = yPos(redT)

  // Below the threshold line activates the stacked mountain.
  hoverInWave = my > yRedPos
  hoverSliceIdx = hoverInWave ? ci : null
  hoverMouseY = my
  hoverMouseX = mx

  // Redraw first so lastHoveredBand is computed.
  draw()

  const hasEvents = t.events.length > 0
  const hasBand = hoverInWave && lastHoveredBand
  const nearNode = Math.abs(yPos(t.balance) - my) < 18 && hasEvents

  if (!nearNode && !hasBand) {
    infoBarData.value = null
    return
  }

  const days = daysBetween(props.data[0].date, t.date)
  const zone: 'safe' | 'tight' | 'danger' =
    t.balance < redT ? 'danger' : t.balance < yellowT ? 'tight' : 'safe'

  let name: string
  let amount: number
  let isIncome: boolean

  if (hasBand && lastHoveredBand) {
    name = lastHoveredBand.name
    amount = lastHoveredBand.amount
    isIncome = false
  } else {
    const ev = t.events[0]
    name = ev.name
    amount = Math.abs(ev.amount)
    isIncome = ev.amount > 0
  }

  infoBarData.value = {
    date: t.date,
    dayOffset: days,
    balance: t.balance,
    balanceZone: zone,
    name,
    amount,
    isIncome,
  }
}

// ── Mouse interactions ──
let dragStartX = 0
let dragStartView = 0

function onMouseDown(e: MouseEvent) {
  isDragging.value = true
  dragStartX = e.clientX
  dragStartView = viewStart
  infoBarData.value = null
  window.addEventListener('mousemove', onWindowMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

function onWindowMouseMove(e: MouseEvent) {
  if (!isDragging.value || !wrapRef.value) return
  const dx = e.clientX - dragStartX
  const pxPerDay = wrapRef.value.clientWidth / viewCount
  viewStart = Math.round(dragStartView - dx / pxPerDay)
  clampView()
  draw()
}

function onMouseUp() {
  isDragging.value = false
  window.removeEventListener('mousemove', onWindowMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
}

function onMouseMove(e: MouseEvent) {
  if (isDragging.value) return
  updateInfoBar(e.clientX, e.clientY)
}

function onMouseLeave() {
  infoBarData.value = null
  hoverInWave = false
  hoverSliceIdx = null
  draw()
}

function onWheel(e: WheelEvent) {
  if (!wrapRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const pct = (e.clientX - rect.left) / rect.width
  const delta = e.deltaY > 0 ? 5 : -5
  const oldCount = viewCount
  viewCount = Math.max(10, Math.min(props.data.length, viewCount + delta))
  const shift = Math.round((viewCount - oldCount) * pct)
  viewStart -= shift
  clampView()
  draw()
}

// ── Touch interactions ──
let lastPinchDist = 0
let touchStartView = 0
let touchStartCount = 0
let touchDragging = false
let touchStartX = 0
let touchDragStartView = 0

function onTouchStart(e: TouchEvent) {
  if (e.touches.length === 2) {
    const dx = e.touches[0].clientX - e.touches[1].clientX
    const dy = e.touches[0].clientY - e.touches[1].clientY
    lastPinchDist = Math.sqrt(dx * dx + dy * dy)
    touchStartView = viewStart
    touchStartCount = viewCount
  } else if (e.touches.length === 1) {
    touchDragging = true
    touchStartX = e.touches[0].clientX
    touchDragStartView = viewStart
  }
}

function onTouchMove(e: TouchEvent) {
  if (e.touches.length === 2 && lastPinchDist > 0) {
    const dx = e.touches[0].clientX - e.touches[1].clientX
    const dy = e.touches[0].clientY - e.touches[1].clientY
    const dist = Math.sqrt(dx * dx + dy * dy)
    const scale = dist / lastPinchDist
    viewCount = Math.max(10, Math.min(props.data.length, Math.round(touchStartCount / scale)))
    const mid = (e.touches[0].clientX + e.touches[1].clientX) / 2
    const rect = wrapRef.value!.getBoundingClientRect()
    const pct = (mid - rect.left) / rect.width
    viewStart = Math.round(touchStartView + (touchStartCount - viewCount) * pct)
    clampView()
    draw()
  } else if (e.touches.length === 1 && touchDragging && wrapRef.value) {
    const dx = e.touches[0].clientX - touchStartX
    const pxPerDay = wrapRef.value.clientWidth / viewCount
    viewStart = Math.round(touchDragStartView - dx / pxPerDay)
    clampView()
    draw()
  }
}

function onTouchEnd() {
  touchDragging = false
  lastPinchDist = 0
}

function handleResize() { draw() }

onMounted(() => { window.addEventListener('resize', handleResize) })
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('mousemove', onWindowMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
})

watch(() => props.data, () => {
  viewStart = 0
  viewCount = Math.min(30, props.data.length)
  nextTick(draw)
}, { immediate: true })

watch(() => props.highlightDate, () => { draw() })
watch(() => props.highlightedCause, () => { draw() })

watch(() => props.pulseDate, (val) => {
  if (val) startPulse()
  else draw()
})

/** Zoom the chart so it spans from index 0 through the target date + 10 calendar days. */
function zoomToDate(targetDate: string) {
  if (!props.data.length) return

  const targetCal = parseLocalDate(targetDate).getTime()
  const bufferMs = 10 * 864e5
  const endCal = targetCal + bufferMs

  let endIdx = props.data.length - 1
  for (let i = props.data.length - 1; i >= 0; i--) {
    if (parseLocalDate(props.data[i].date).getTime() <= endCal) {
      endIdx = i
      break
    }
  }

  viewStart = 0
  viewCount = Math.max(10, endIdx + 1)
  clampView()
  draw()

  wrapRef.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

defineExpose({ zoomToDate })
</script>

<style scoped>
.sh {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin: 20px 0 10px;
}

.sh-t {
  font-size: 10px;
  font-weight: 700;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.sh-m {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted);
}

.chart-box {
  background: var(--panel);
  border: 1px solid var(--border);
  height: 340px;
  position: relative;
  overflow: hidden;
  cursor: crosshair;
  touch-action: none;
}

.chart-box.grabbing {
  cursor: grabbing;
}

.chart-box canvas {
  width: 100%;
  height: 100%;
  display: block;
}

@media (max-width: 700px) {
  .chart-box { height: 220px; }
}
</style>
