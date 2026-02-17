<template>
  <div>
    <div class="sh">
      <span class="sh-t">Balance Trajectory</span>
      <span class="sh-m">{{ rangeLabel }}</span>
    </div>
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
      <div class="tt" ref="tipRef" :class="{ show: tipVisible }">
        <div v-html="tipHtml" />
      </div>
    </div>
    <div class="thresh-legend">
      <div class="tl-item"><span class="tl-dot grn" /> Safe</div>
      <div class="tl-item"><span class="tl-dot yel" /> Caution</div>
      <div class="tl-item"><span class="tl-dot red" /> Danger</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import type { TrajectoryPoint } from '@/composables/useDashboard'
import { parseLocalDate } from '@/utils/format'

const props = defineProps<{
  data: TrajectoryPoint[]
  highlightDate?: string | null
  pulseDate?: string | null
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const wrapRef = ref<HTMLDivElement | null>(null)
const tipRef = ref<HTMLDivElement | null>(null)
const tipVisible = ref(false)
const tipHtml = ref('')
const isDragging = ref(false)
const rangeLabel = ref('')

// Windowed view state.
let viewStart = 0
let viewCount = 30

const fmtShort = (n: number) =>
  '$' + Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })

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

// Store chart mapping for tooltip hit-testing.
let chartState: {
  xPos: (i: number) => number
  yPos: (v: number) => number
  slice: TrajectoryPoint[]
  redT: number
  yellowT: number
} | null = null

function clampView() {
  if (viewStart < 0) viewStart = 0
  if (viewStart > props.data.length - viewCount) viewStart = props.data.length - viewCount
  if (viewStart < 0) viewStart = 0
}

/** Compute threshold for a visible slice.
 *  Splits the window into pay periods, sums expenses in each, and takes the
 *  max as the "high water mark" -- the most you need to survive the tightest
 *  pay period visible. Yellow = red + 1000. */
function computeWindowThreshold(slice: TrajectoryPoint[]): { red: number; yellow: number } {
  // Find paycheck indices within the slice.
  const payIndices: number[] = []
  for (let i = 0; i < slice.length; i++) {
    if (slice[i].events.some(e => e.amount > 500)) {
      payIndices.push(i)
    }
  }

  // Build pay windows. Each window runs from one payday to the day before next.
  // Before first payday and after last payday are their own windows.
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

  const P = { top: 32, right: 20, bottom: 38, left: 60 }
  const W = rect.width
  const H = rect.height
  const cW = W - P.left - P.right
  const cH = H - P.top - P.bottom
  // Single flat threshold for the visible window.
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
  ctx.fillStyle = 'rgba(248,113,113,.03)'
  ctx.fillRect(P.left, yRed, cW, chartBottom - yRed)

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
  zoneFill(yRed, chartBottom, 'rgba(248,113,113,.07)')

  // Threshold dashed lines.
  ctx.setLineDash([4, 6])
  if (redT > mn && redT < mx) {
    ctx.strokeStyle = 'rgba(248,113,113,.2)'
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(P.left, yRed); ctx.lineTo(P.left + cW, yRed); ctx.stroke()
    ctx.fillStyle = 'rgba(248,113,113,.25)'
    ctx.font = '600 8px Sora'
    ctx.fillText(`DANGER ${fmtShort(redT)}`, P.left + 4, yRed - 3)
  }
  if (yellowT > mn && yellowT < mx) {
    ctx.strokeStyle = 'rgba(251,191,36,.15)'
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(P.left, yYellow); ctx.lineTo(P.left + cW, yYellow); ctx.stroke()
    ctx.fillStyle = 'rgba(251,191,36,.2)'
    ctx.font = '600 8px Sora'
    ctx.fillText(`CAUTION ${fmtShort(yellowT)}`, P.left + 4, yYellow - 3)
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

  // Lowest point marker.
  const lx = xPos(lowI)
  const ly = yPos(slice[lowI].balance)
  ctx.beginPath(); ctx.arc(lx, ly, 12, 0, Math.PI * 2)
  ctx.strokeStyle = 'rgba(248,113,113,.25)'; ctx.lineWidth = 1.5; ctx.stroke()
  ctx.beginPath(); ctx.arc(lx, ly, 4, 0, Math.PI * 2)
  ctx.fillStyle = '#F87171'; ctx.fill()
  const gl = ctx.createRadialGradient(lx, ly, 0, lx, ly, 18)
  gl.addColorStop(0, 'rgba(248,113,113,.15)')
  gl.addColorStop(1, 'rgba(248,113,113,0)')
  ctx.fillStyle = gl
  ctx.beginPath(); ctx.arc(lx, ly, 18, 0, Math.PI * 2); ctx.fill()
  ctx.fillStyle = '#F87171'
  ctx.textAlign = 'center'
  ctx.font = '700 9px Sora'
  ctx.fillText('LOWEST', lx, ly - 16)
  ctx.font = '700 11px IBM Plex Mono'
  ctx.fillText(fmtShort(slice[lowI].balance), lx, ly - 6)
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

// ── Tooltip on hover ──
function showTooltip(clientX: number) {
  if (!chartState || !wrapRef.value || !tipRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const mx = clientX - rect.left
  const { xPos, yPos, slice } = chartState

  let ci = 0
  let cd = Infinity
  slice.forEach((_, i) => {
    const d = Math.abs(xPos(i) - mx)
    if (d < cd) { cd = d; ci = i }
  })

  if (cd > 25) { tipVisible.value = false; return }

  const t = slice[ci]
  const x = xPos(ci)
  const y = yPos(t.balance)
  const dt = parseLocalDate(t.date)
  const dateStr = dt.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  const days = daysBetween(props.data[0].date, t.date)
  const dayLabel = days === 0 ? 'Today' : `+${days}d`

  const bc = t.balance < chartState.redT
    ? 'var(--danger)'
    : t.balance < chartState.yellowT
      ? 'var(--tight)'
      : 'var(--safe)'

  let h = `<div style="font-weight:700;color:var(--bright);margin-bottom:3px">${dateStr} \u00B7 ${dayLabel}</div>`
  h += `<div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:${bc};margin-bottom:5px">${fmtShort(t.balance)}</div>`
  for (const ev of t.events) {
    const c = ev.amount > 0 ? 'var(--income)' : 'var(--danger)'
    const sign = ev.amount > 0 ? '+' : '-'
    h += `<div style="font-size:10px;color:var(--dim);display:flex;justify-content:space-between;gap:8px"><span>${ev.name}</span><span style="font-family:var(--font-mono);font-weight:700;color:${c}">${sign}${fmtShort(ev.amount)}</span></div>`
  }

  tipHtml.value = h
  tipVisible.value = true
  let tx = x + 12
  if (tx + 180 > rect.width - 10) tx = x - 190
  tipRef.value.style.left = `${tx}px`
  tipRef.value.style.top = `${Math.max(6, y - 30)}px`
}

// ── Mouse interactions ──
let dragStartX = 0
let dragStartView = 0

function onMouseDown(e: MouseEvent) {
  isDragging.value = true
  dragStartX = e.clientX
  dragStartView = viewStart
  tipVisible.value = false
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
  showTooltip(e.clientX)
}

function onMouseLeave() {
  tipVisible.value = false
}

function onWheel(e: WheelEvent) {
  if (!wrapRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const pct = (e.clientX - rect.left) / rect.width
  const delta = e.deltaY > 0 ? 5 : -5
  const oldCount = viewCount
  viewCount = Math.max(10, Math.min(props.data.length, viewCount + delta))
  // Keep the point under cursor stable.
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

// Redraw when highlight changes (event list hover).
watch(() => props.highlightDate, () => { draw() })

// Start pulse animation when pulseDate changes.
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

  // Find last data index whose date <= targetDate + 10 days.
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

  // Scroll the chart into view.
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
  backdrop-filter: blur(16px);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  height: 280px;
  position: relative;
  overflow: hidden;
  cursor: grab;
  box-shadow: var(--shadow-card);
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

.tt {
  position: absolute;
  pointer-events: none;
  opacity: 0;
  backdrop-filter: blur(16px);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 11px;
  min-width: 170px;
  transition: opacity 0.1s;
  z-index: 5;
  box-shadow: var(--shadow-tooltip);
}

.tt.show {
  opacity: 1;
}

.thresh-legend {
  display: flex;
  gap: 20px;
  align-items: center;
  margin-top: 8px;
}

.tl-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 9px;
  color: var(--dim);
  font-weight: 600;
}

.tl-dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}

.tl-dot.red { background: var(--danger); }
.tl-dot.yel { background: var(--tight); }
.tl-dot.grn { background: var(--safe); }

@media (max-width: 700px) {
  .chart-box { height: 200px; }
}
</style>
