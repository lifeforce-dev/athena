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
import type { TrajectoryPoint } from '@/utils/trajectory'
import type { WorstWindow, DailyExpenseEntry } from '@/composables/useExpenseAnalysis'
import type { InfoBarData } from '@/components/InfoBar.vue'
import InfoBar from '@/components/InfoBar.vue'
import { parseLocalDate, daysBetween } from '@/utils/format'
import {
  type ChartLayout, type HoverState, type HoveredBand,
  buildLayout, buildRangeLabel,
  drawZoneBands, drawExpenseWave, drawTrajectoryFill,
  drawThresholdLines, drawGrid, drawTrajectoryLine,
  drawEventDots, drawLowestPoint, drawXAxis,
} from '@/utils/chartRendering'

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

// Hover + drawing state shared between interaction and rendering.
const hover: HoverState = { inWave: false, sliceIdx: null, mouseY: 0, mouseX: 0 }
let currentLayout: ChartLayout | null = null
let lastHoveredBand: HoveredBand | null = null

// Pulse animation state.
let pulseStartTime = 0
let pulseAnimId = 0
const PULSE_DURATION = 2500

function clampView() {
  if (viewStart < 0) viewStart = 0
  if (viewStart > props.data.length - viewCount) viewStart = props.data.length - viewCount
  if (viewStart < 0) viewStart = 0
}

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

// ── Drawing ──

function draw(pulseElapsed?: number) {
  const canvas = canvasRef.value
  const wrap = wrapRef.value
  if (!canvas || !wrap || !props.data.length) return

  clampView()
  const layout = buildLayout(canvas, wrap, props.data, viewStart, viewCount)
  if (!layout) return

  currentLayout = layout
  rangeLabel.value = buildRangeLabel(layout.slice)

  drawZoneBands(layout)

  lastHoveredBand = drawExpenseWave(layout, {
    worstWindow: props.worstWindow ?? null,
    expenseWave: props.expenseWave ?? [],
    dailyExpenseStack: props.dailyExpenseStack ?? [],
    masterExpenseOrder: props.masterExpenseOrder ?? [],
    masterColorMap: props.masterColorMap ?? {},
  }, hover)

  drawTrajectoryFill(layout)
  drawThresholdLines(layout)
  drawGrid(layout)
  drawTrajectoryLine(layout)

  drawEventDots(layout, {
    highlightDate: props.highlightDate,
    pulseDate: props.pulseDate,
    highlightedCause: props.highlightedCause,
    worstWindow: props.worstWindow,
    pulseElapsed,
  })

  drawLowestPoint(layout)
  drawXAxis(layout, props.data[0].date)
}

// ── Info bar update on hover ──

/** Find the trajectory point closest to hoverDate that has an event matching expenseName. */
function findClosestOccurrence(hoverDate: string, expenseName: string): { date: string; amount: number } | null {
  const hoverTime = parseLocalDate(hoverDate).getTime()
  let best: { date: string; amount: number; dist: number } | null = null

  for (const point of props.data) {
    for (const event of point.events) {
      if (event.name === expenseName && event.amount < 0) {
        const dist = Math.abs(parseLocalDate(point.date).getTime() - hoverTime)

        if (!best || dist < best.dist) {
          best = { date: point.date, amount: Math.abs(event.amount), dist }
        }
      }
    }
  }

  return best ? { date: best.date, amount: best.amount } : null
}

function updateInfoBar(clientX: number, clientY: number) {
  if (!currentLayout || !wrapRef.value) return

  const rect = wrapRef.value.getBoundingClientRect()
  const mouseX = clientX - rect.left
  const mouseY = clientY - rect.top
  const { xPos, yPos, slice, redThreshold, yellowThreshold } = currentLayout

  let closestIndex = 0
  let closestDistance = Infinity
  slice.forEach((_, i) => {
    const distance = Math.abs(xPos(i) - mouseX)
    if (distance < closestDistance) { closestDistance = distance; closestIndex = i }
  })

  // Scale rejection threshold to point spacing so zoomed-in views stay interactive.
  const pointSpacing = slice.length > 1 ? Math.abs(xPos(1) - xPos(0)) : 50
  const rejectThreshold = Math.max(25, pointSpacing * 0.6)

  if (closestDistance > rejectThreshold) {
    infoBarData.value = null
    hover.inWave = false
    hover.sliceIdx = null
    draw()
    return
  }

  const point = slice[closestIndex]
  const yRedPos = yPos(redThreshold)

  // Below the threshold line activates the stacked mountain.
  hover.inWave = mouseY > yRedPos
  hover.sliceIdx = hover.inWave ? closestIndex : null
  hover.mouseY = mouseY
  hover.mouseX = mouseX

  // Redraw first so lastHoveredBand is computed.
  draw()

  const days = daysBetween(props.data[0].date, point.date)
  const zone: 'safe' | 'tight' | 'danger' =
    point.balance < redThreshold ? 'danger' : point.balance < yellowThreshold ? 'tight' : 'safe'

  // Baseline is always populated.
  const result: InfoBarData = {
    date: point.date,
    dayOffset: days,
    balance: point.balance,
    balanceZone: zone,
  }

  const hasBand = hover.inWave && lastHoveredBand
  const hasEvents = point.events.length > 0
  const nearNode = Math.abs(yPos(point.balance) - mouseY) < 18 && hasEvents

  if (hasBand && lastHoveredBand) {
    // Find the closest actual occurrence of this expense.
    const occurrence = findClosestOccurrence(point.date, lastHoveredBand.name)

    if (occurrence) {
      result.band = {
        name: lastHoveredBand.name,
        occurrenceDate: occurrence.date,
        occurrenceDayOffset: daysBetween(props.data[0].date, occurrence.date),
        amount: occurrence.amount,
      }
    }
  } else if (nearNode) {
    const event = point.events[0]
    result.event = {
      name: event.name,
      amount: Math.abs(event.amount),
      isIncome: event.amount > 0,
    }
  }

  infoBarData.value = result
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
  const dragDelta = e.clientX - dragStartX
  const pxPerDay = wrapRef.value.clientWidth / viewCount
  viewStart = Math.round(dragStartView - dragDelta / pxPerDay)
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
  hover.inWave = false
  hover.sliceIdx = null
  draw()
}

function onWheel(e: WheelEvent) {
  if (!wrapRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const anchorPercent = (e.clientX - rect.left) / rect.width
  const delta = e.deltaY > 0 ? 5 : -5
  const oldCount = viewCount
  viewCount = Math.max(10, Math.min(props.data.length, viewCount + delta))
  const shift = Math.round((viewCount - oldCount) * anchorPercent)
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
    const deltaX = e.touches[0].clientX - e.touches[1].clientX
    const deltaY = e.touches[0].clientY - e.touches[1].clientY
    lastPinchDist = Math.sqrt(deltaX * deltaX + deltaY * deltaY)
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
    const deltaX = e.touches[0].clientX - e.touches[1].clientX
    const deltaY = e.touches[0].clientY - e.touches[1].clientY
    const dist = Math.sqrt(deltaX * deltaX + deltaY * deltaY)
    const scale = dist / lastPinchDist
    viewCount = Math.max(10, Math.min(props.data.length, Math.round(touchStartCount / scale)))
    const mid = (e.touches[0].clientX + e.touches[1].clientX) / 2
    const rect = wrapRef.value!.getBoundingClientRect()
    const anchorPercent = (mid - rect.left) / rect.width
    viewStart = Math.round(touchStartView + (touchStartCount - viewCount) * anchorPercent)
    clampView()
    draw()
  } else if (e.touches.length === 1 && touchDragging && wrapRef.value) {
    const dragDelta = e.touches[0].clientX - touchStartX
    const pxPerDay = wrapRef.value.clientWidth / viewCount
    viewStart = Math.round(touchDragStartView - dragDelta / pxPerDay)
    clampView()
    draw()
  }
}

function onTouchEnd() {
  touchDragging = false
  lastPinchDist = 0
}

// ── Lifecycle ──

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
