<template>
  <div>
    <div class="sh">
      <span class="sh-t">Trajectory</span>
      <span class="sh-m">{{ rangeLabel }}</span>
    </div>
    <div class="chart-box" ref="wrapRef" :class="{ grabbing: isDragging }">
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
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const wrapRef = ref<HTMLDivElement | null>(null)
const tipRef = ref<HTMLDivElement | null>(null)
const tipVisible = ref(false)
const tipHtml = ref('')
const isDragging = ref(false)

const rangeLabel = ref('')

const fmtShort = (n: number) =>
  '$' + Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })

const shortDate = (d: string) =>
  parseLocalDate(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

// Store chart mapping for tooltip hit-testing.
let chartData: {
  xPos: (i: number) => number
  yPos: (v: number) => number
  slice: TrajectoryPoint[]
} | null = null

function computeThresholds(slice: TrajectoryPoint[]) {
  // Find first rent event and first large income after it to define survival window.
  const rentIdx = slice.findIndex(pt => pt.events.some(e => e.name === 'Rent'))
  if (rentIdx < 0) return { red: 3000, yellow: 4000 }

  const rentAmount = Math.abs(slice[rentIdx].events.find(e => e.name === 'Rent')!.amount)
  const payIdx = slice.findIndex((pt, i) => i > rentIdx && pt.events.some(e => e.amount > 1000))
  const end = payIdx >= 0 ? payIdx : slice.length

  let windowBills = 0
  for (let i = rentIdx; i < end; i++) {
    for (const ev of slice[i].events) {
      if (ev.amount < 0 && ev.name !== 'Rent') {
        windowBills += Math.abs(ev.amount)
      }
    }
  }

  const red = rentAmount + windowBills
  return { red, yellow: red + 1000 }
}

function draw() {
  const canvas = canvasRef.value
  const wrap = wrapRef.value
  if (!canvas || !wrap || !props.data.length) return

  const ctx = canvas.getContext('2d')!
  const slice = props.data
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
  const mn = 0
  const mx = Math.max(...slice.map(t => t.balance)) * 1.1
  const xPos = (i: number) => P.left + (i / (slice.length - 1)) * cW
  const yPos = (v: number) => P.top + (1 - (v - mn) / (mx - mn)) * cH
  const chartBottom = P.top + cH

  chartData = { xPos, yPos, slice }

  // Update range label.
  rangeLabel.value = `${shortDate(slice[0].date)} - ${shortDate(slice[slice.length - 1].date)}`

  ctx.clearRect(0, 0, W, H)

  const { red: redT, yellow: yellowT } = computeThresholds(slice)
  const yRed = yPos(redT)
  const yYellow = yPos(yellowT)

  // Zone bands.
  if (yellowT < mx) {
    ctx.fillStyle = 'rgba(52,211,153,.02)'
    ctx.fillRect(P.left, P.top, cW, yYellow - P.top)
  }
  ctx.fillStyle = 'rgba(251,191,36,.02)'
  ctx.fillRect(P.left, yYellow, cW, yRed - yYellow)
  ctx.fillStyle = 'rgba(248,113,113,.03)'
  ctx.fillRect(P.left, yRed, cW, chartBottom - yRed)

  // Zone fills under trajectory.
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

  // Threshold lines.
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

  // Grid.
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
    const isRent = t.events.some(e => e.name === 'Rent')
    let c = 'rgba(184,190,201,.4)'
    let r = 3
    if (inc) { c = '#A78BFA'; r = 5 }
    if (isRent) { c = '#FBBF24'; r = 5 }
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
    ctx.fillStyle = 'rgba(90,99,120,.4)'
    ctx.font = '9px Sora'
    ctx.fillText(shortDate(t.date), xPos(i), chartBottom + 14)
  })
  ctx.textAlign = 'left'
}

function handleMouseMove(e: MouseEvent) {
  if (!chartData || !wrapRef.value || !tipRef.value) return
  const rect = wrapRef.value.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const { xPos, yPos, slice } = chartData

  let ci = 0
  let cd = Infinity
  slice.forEach((_, i) => {
    const d = Math.abs(xPos(i) - mx)
    if (d < cd) { cd = d; ci = i }
  })

  if (cd > 25) {
    tipVisible.value = false
    return
  }

  const t = slice[ci]
  const x = xPos(ci)
  const y = yPos(t.balance)
  const dt = parseLocalDate(t.date)
  const dateStr = dt.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })

  let h = `<div style="font-weight:700;color:var(--bright);margin-bottom:3px">${dateStr}</div>`
  h += `<div style="font-family:var(--font-mono);font-size:16px;font-weight:700;color:var(--bright);margin-bottom:5px">${fmtShort(t.balance)}</div>`
  for (const ev of t.events) {
    const c = ev.amount > 0 ? 'var(--income)' : 'var(--danger)'
    const sign = ev.amount > 0 ? '+' : '-'
    h += `<div style="font-size:10px;color:var(--dim);display:flex;justify-content:space-between;gap:8px"><span>${ev.name}</span><span style="font-family:var(--font-mono);font-weight:700;color:${c}">${sign}${fmtShort(ev.amount)}</span></div>`
  }

  tipHtml.value = h
  tipVisible.value = true

  if (tipRef.value) {
    let tx = x + 12
    if (tx + 180 > rect.width - 10) tx = x - 190
    tipRef.value.style.left = `${tx}px`
    tipRef.value.style.top = `${Math.max(6, y - 30)}px`
  }
}

function handleMouseLeave() {
  tipVisible.value = false
}

function handleResize() {
  draw()
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

watch(() => props.data, () => {
  nextTick(draw)
}, { immediate: true })
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
  cursor: crosshair;
  box-shadow: var(--shadow-card);
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
