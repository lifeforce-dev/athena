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

// Store chart mapping for tooltip hit-testing.
let chartState: {
  xPos: (i: number) => number
  yPos: (v: number) => number
  slice: TrajectoryPoint[]
  thresholds: { red: number; yellow: number }[]
} | null = null

function clampView() {
  if (viewStart < 0) viewStart = 0
  if (viewStart > props.data.length - viewCount) viewStart = props.data.length - viewCount
  if (viewStart < 0) viewStart = 0
}

/** Compute per-point danger/caution thresholds.
 *  At each point, red = sum of remaining expenses before the next paycheck.
 *  Yellow = red + 1000. Thresholds step down as expenses are paid. */
function computeDynamicThresholds(allData: TrajectoryPoint[]): { red: number; yellow: number }[] {
  // Identify paycheck days (large income events).
  const paycheckIndices: number[] = []
  for (let i = 0; i < allData.length; i++) {
    if (allData[i].events.some(e => e.amount > 500)) {
      paycheckIndices.push(i)
    }
  }

  // Per-day expense totals and prefix sums for O(1) range queries.
  const dayExpense = allData.map(pt =>
    pt.events.reduce((sum, e) => sum + (e.amount < 0 ? Math.abs(e.amount) : 0), 0)
  )
  const prefix: number[] = [0]
  for (let i = 0; i < dayExpense.length; i++) {
    prefix.push(prefix[i] + dayExpense[i])
  }
  const rangeExpense = (a: number, b: number) => (a > b ? 0 : prefix[b + 1] - prefix[a])

  const result: { red: number; yellow: number }[] = []
  let payPtr = 0

  for (let i = 0; i < allData.length; i++) {
    // Advance to first paycheck strictly after this point.
    while (payPtr < paycheckIndices.length && paycheckIndices[payPtr] <= i) payPtr++
    const nextPayIdx = payPtr < paycheckIndices.length ? paycheckIndices[payPtr] : allData.length

    // Sum expenses from the day after this point through the day before payday.
    const red = Math.round(rangeExpense(i + 1, nextPayIdx - 1))
    result.push({ red, yellow: red + 1000 })
  }

  return result
}

function draw() {
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
  // Per-point thresholds computed before Y scaling.
  const allThresholds = computeDynamicThresholds(props.data)
  const sliceThresholds = allThresholds.slice(viewStart, viewStart + viewCount)
  const mn = 0
  const maxBal = Math.max(...slice.map(t => t.balance))
  const maxYellow = Math.max(...sliceThresholds.map(t => t.yellow))
  const mx = Math.max(maxBal, maxYellow) * 1.1
  const xPos = (i: number) => P.left + (i / Math.max(slice.length - 1, 1)) * cW
  const yPos = (v: number) => P.top + (1 - (v - mn) / (mx - mn)) * cH
  const chartBottom = P.top + cH

  chartState = { xPos, yPos, slice, thresholds: sliceThresholds }
  const calDays = daysBetween(slice[0].date, slice[slice.length - 1].date)
  rangeLabel.value = `${shortDate(slice[0].date)} \u2192 ${shortDate(slice[slice.length - 1].date)} \u00B7 ${calDays} days`

  ctx.clearRect(0, 0, W, H)

  // Generate step coordinates for dynamic threshold lines.
  const redVals = sliceThresholds.map(t => t.red)
  const yellowVals = sliceThresholds.map(t => t.yellow)
  const traceStep = (vals: number[]): [number, number][] => {
    const pts: [number, number][] = []
    for (let i = 0; i < vals.length; i++) {
      if (i > 0) pts.push([xPos(i), yPos(vals[i - 1])])
      pts.push([xPos(i), yPos(vals[i])])
    }
    return pts
  }
  const redStep = traceStep(redVals)
  const yellowStep = traceStep(yellowVals)

  // Red zone fill: below red step to chart bottom.
  ctx.beginPath()
  ctx.moveTo(xPos(0), chartBottom)
  for (const [x, y] of redStep) ctx.lineTo(x, y)
  ctx.lineTo(xPos(slice.length - 1), chartBottom)
  ctx.closePath()
  ctx.fillStyle = 'rgba(248,113,113,.03)'
  ctx.fill()

  // Yellow zone fill: between yellow and red steps.
  if (yellowStep.length && redStep.length) {
    ctx.beginPath()
    ctx.moveTo(yellowStep[0][0], yellowStep[0][1])
    for (let i = 1; i < yellowStep.length; i++) ctx.lineTo(yellowStep[i][0], yellowStep[i][1])
    for (let i = redStep.length - 1; i >= 0; i--) ctx.lineTo(redStep[i][0], redStep[i][1])
    ctx.closePath()
    ctx.fillStyle = 'rgba(251,191,36,.02)'
    ctx.fill()
  }

  // Green zone fill: above yellow step to chart top.
  ctx.beginPath()
  ctx.moveTo(xPos(0), P.top)
  for (const [x, y] of yellowStep) ctx.lineTo(x, y)
  ctx.lineTo(xPos(slice.length - 1), P.top)
  ctx.closePath()
  ctx.fillStyle = 'rgba(52,211,153,.02)'
  ctx.fill()

  // Per-segment trajectory fill colored by zone.
  for (let i = 0; i < slice.length - 1; i++) {
    const bal = Math.min(slice[i].balance, slice[i + 1].balance)
    const th = sliceThresholds[i]
    const color = bal < th.red
      ? 'rgba(248,113,113,.07)'
      : bal < th.yellow
        ? 'rgba(251,191,36,.06)'
        : 'rgba(52,211,153,.06)'
    ctx.beginPath()
    ctx.moveTo(xPos(i), chartBottom)
    ctx.lineTo(xPos(i), yPos(slice[i].balance))
    ctx.lineTo(xPos(i + 1), yPos(slice[i + 1].balance))
    ctx.lineTo(xPos(i + 1), chartBottom)
    ctx.closePath()
    ctx.fillStyle = color
    ctx.fill()
  }

  // Stepped threshold dashed lines.
  ctx.setLineDash([4, 6])
  ctx.strokeStyle = 'rgba(248,113,113,.2)'
  ctx.lineWidth = 1
  ctx.beginPath()
  for (let i = 0; i < redStep.length; i++) {
    if (i === 0) ctx.moveTo(redStep[i][0], redStep[i][1])
    else ctx.lineTo(redStep[i][0], redStep[i][1])
  }
  ctx.stroke()

  ctx.strokeStyle = 'rgba(251,191,36,.15)'
  ctx.lineWidth = 1
  ctx.beginPath()
  for (let i = 0; i < yellowStep.length; i++) {
    if (i === 0) ctx.moveTo(yellowStep[i][0], yellowStep[i][1])
    else ctx.lineTo(yellowStep[i][0], yellowStep[i][1])
  }
  ctx.stroke()
  ctx.setLineDash([])

  // Threshold labels at left edge.
  if (redVals[0] > mn) {
    ctx.fillStyle = 'rgba(248,113,113,.25)'
    ctx.font = '600 8px Sora'
    ctx.fillText(`DANGER ${fmtShort(redVals[0])}`, P.left + 4, yPos(redVals[0]) - 3)
  }
  if (yellowVals[0] > mn) {
    ctx.fillStyle = 'rgba(251,191,36,.2)'
    ctx.font = '600 8px Sora'
    ctx.fillText(`CAUTION ${fmtShort(yellowVals[0])}`, P.left + 4, yPos(yellowVals[0]) - 3)
  }

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

  const th = chartState.thresholds[ci] ?? { red: 0, yellow: 1000 }
  const bc = t.balance < th.red
    ? 'var(--danger)'
    : t.balance < th.yellow
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
