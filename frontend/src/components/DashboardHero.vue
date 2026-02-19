<template>
  <section class="hero" :class="statusClass">
    <!-- Balance headline -->
    <div class="hero-top" data-tour="balance" @click="startEdit">
      <template v-if="!editing">
        <div class="hero-balance">{{ formatDollars(currentBalance) }}</div>
        <div class="hero-bal-lbl">Current Balance</div>
      </template>
      <template v-else>
        <input
          ref="inputRef"
          v-model="editValue"
          class="hero-input"
          type="text"
          inputmode="decimal"
          placeholder="0"
          @keydown.enter="saveBalance"
          @keydown.escape="cancelEdit"
          @blur="cancelEdit"
        />
        <div class="hero-edit-actions">
          <button class="hero-save" @mousedown.prevent="saveBalance">Save</button>
          <span class="hero-cancel" @mousedown.prevent="cancelEdit">Esc</span>
        </div>
      </template>
    </div>

    <!-- Shield gauge -->
    <div class="gauge-wrap" data-tour="gauge">
      <div class="gauge-header">
        <div class="gauge-verdict" :class="statusClass">{{ verdict }}</div>
        <div>
          <span class="gauge-days">{{ daysCovered }}</span>
          <span class="gauge-days-lbl"> days projected</span>
        </div>
      </div>
      <div class="gauge-track" :style="{ '--gauge-pct': gaugePct + '%' }">
        <div class="gauge-marker" :style="{ left: gaugePct + '%' }" />
      </div>
      <div class="gauge-labels">
        <span class="gauge-lbl" style="color: var(--danger)">Critical</span>
        <span class="gauge-lbl" style="color: var(--tight)">Tight</span>
        <span class="gauge-lbl" style="color: var(--safe)">Comfortable</span>
      </div>
    </div>

    <!-- Stats strip -->
    <div class="stats-strip">
      <div class="stat-cell">
        <div class="stat-val" :style="{ color: endColor }">{{ formatDollars(endBalance) }}</div>
        <div class="stat-lbl">After Window</div>
      </div>
      <div class="stat-cell">
        <div class="stat-val" style="color: var(--danger)">{{ formatDollars(lowestBalance) }}</div>
        <div class="stat-lbl">Lowest Point</div>
        <div class="stat-sub">{{ lowestDate }}</div>
      </div>
      <div class="stat-cell">
        <div class="stat-val" :style="{ color: netColor }">{{ netLabel }}</div>
        <div class="stat-lbl">Net Change</div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { parseLocalDate, formatDollars } from '@/utils/format'

const props = defineProps<{
  currentBalance: number
  endBalance: number
  netChange: number
  lowestBalance: number
  lowestDate: string
  daysCovered: number
}>()

const emit = defineEmits<{
  updateBalance: [balance: number]
}>()

const editing = ref(false)
const editValue = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

function startEdit() {
  if (editing.value) return
  editing.value = true
  editValue.value = Math.round(props.currentBalance).toString()
  nextTick(() => {
    inputRef.value?.focus()
    inputRef.value?.select()
  })
}

function cancelEdit() {
  editing.value = false
}

function saveBalance() {
  const raw = editValue.value.replace(/[,$\s]/g, '')
  const num = parseFloat(raw)
  if (isNaN(num) || num < 0) return
  editing.value = false
  emit('updateBalance', num)
}

const statusClass = computed(() => {
  if (props.lowestBalance < 0) return 'danger'
  if (props.lowestBalance < 3000) return 'tight'
  return 'safe'
})

const verdict = computed(() => {
  if (statusClass.value === 'danger') return 'Critical'
  if (statusClass.value === 'tight') return 'Tight'
  return 'Comfortable'
})

const endColor = computed(() =>
  props.endBalance >= props.currentBalance ? 'var(--safe)' : 'var(--danger)'
)

const netColor = computed(() =>
  props.netChange >= 0 ? 'var(--safe)' : 'var(--danger)'
)

const netLabel = computed(() => {
  const sign = props.netChange >= 0 ? '+' : '-'
  return `${sign}${formatDollars(props.netChange)}`
})

const lowestDate = computed(() => {
  if (!props.lowestDate) return ''
  return parseLocalDate(props.lowestDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
})

/** Gauge fill: daysCovered as a percentage of the projection window (capped at 90 days). */
const gaugePct = computed(() => Math.min(100, Math.round((props.daysCovered / 90) * 100)))
</script>

<style scoped>
.hero {
  padding: 48px 0 40px;
  position: relative;
  overflow: hidden;
}

.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.hero.safe::before {
  background: radial-gradient(ellipse 50% 35% at 50% 0%, var(--safe-glow), transparent);
}

.hero.tight::before {
  background: radial-gradient(ellipse 50% 35% at 50% 0%, var(--tight-glow), transparent);
}

.hero.danger::before {
  background: radial-gradient(ellipse 50% 35% at 50% 0%, var(--danger-glow), transparent);
}

/* ── Balance headline ── */

.hero-top {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 1;
  cursor: pointer;
}

.hero-balance {
  font-family: var(--font-mono);
  font-size: 44px;
  font-weight: 700;
  color: var(--bright);
  letter-spacing: -0.02em;
  transition: opacity 0.15s;
}

.hero-top:hover .hero-balance {
  opacity: 0.8;
}

.hero-bal-lbl {
  font-size: 9px;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin-top: 2px;
}

.hero-input {
  font-family: var(--font-mono);
  font-size: 44px;
  font-weight: 700;
  color: var(--bright);
  background: transparent;
  border: none;
  border-bottom: 1px solid rgba(232, 236, 242, 0.2);
  text-align: center;
  width: 260px;
  outline: none;
  padding: 0 0 4px;
}

.hero-input::placeholder {
  color: var(--muted);
}

.hero-edit-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.hero-save {
  background: none;
  border: 1px solid rgba(52, 211, 153, 0.25);
  color: var(--safe);
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 3px 10px;
  cursor: pointer;
  font-family: var(--font-sans);
}

.hero-save:hover {
  background: rgba(52, 211, 153, 0.08);
}

.hero-cancel {
  font-size: 8px;
  color: var(--muted);
  cursor: pointer;
}

/* ── Shield gauge ── */

.gauge-wrap {
  position: relative;
  z-index: 1;
  margin-top: 28px;
  padding: 0 4px;
}

.gauge-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 10px;
}

.gauge-verdict {
  font-size: 16px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.gauge-verdict.safe { color: var(--safe); }
.gauge-verdict.tight { color: var(--tight); }
.gauge-verdict.danger { color: var(--danger); }

.gauge-days {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--bright);
}

.gauge-days-lbl {
  font-size: 9px;
  color: var(--dim);
  letter-spacing: 0.08em;
}

.gauge-track {
  position: relative;
  height: 8px;
  background: linear-gradient(90deg, var(--danger) 0%, var(--tight) 40%, var(--safe) 85%);
  overflow: hidden;
}

.gauge-track::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  height: 100%;
  width: calc(100% - var(--gauge-pct, 0%));
  background: var(--muted);
  transition: width 0.6s ease;
}

.gauge-marker {
  position: absolute;
  top: -4px;
  width: 2px;
  height: 16px;
  background: var(--bright);
  transform: translateX(-50%);
  box-shadow: 0 0 6px rgba(232, 236, 242, 0.3);
}

.gauge-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
}

.gauge-lbl {
  font-size: 8px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
}

/* ── Stats strip ── */

.stats-strip {
  display: flex;
  gap: 1px;
  margin-top: 32px;
  position: relative;
  z-index: 1;
  background: var(--border);
}

.stat-cell {
  flex: 1;
  background: var(--panel);
  padding: 14px 12px;
  text-align: center;
}

.stat-val {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 700;
}

.stat-lbl {
  font-size: 8px;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: 3px;
  font-weight: 700;
}

.stat-sub {
  font-size: 8px;
  color: var(--muted);
  font-family: var(--font-mono);
  margin-top: 1px;
}

@media (max-width: 700px) {
  .hero-balance { font-size: 32px; }
  .hero-input { font-size: 32px; width: 200px; }
  .stats-strip { flex-direction: column; }
}
</style>
