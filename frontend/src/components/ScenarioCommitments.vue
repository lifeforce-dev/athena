<template>
  <div class="rails-panel">
    <!-- Income -->
    <div v-if="incomeItems.length">
      <div class="sec-hdr">
        <span class="sec-title">Income ({{ incomeItems.length }})</span>
        <span class="sec-total income">{{ formatSigned(scenarioIncome) }}/mo</span>
      </div>
      <div class="rail-list">
        <div
          v-for="item in incomeItems"
          :key="item.id"
          class="rail"
          :class="{ off: !isActive(item.id), modified: isModified(item.id) }"
          :style="{ '--weight': weight(item) + '%' }"
        >
          <div class="rail-toggle" @click="toggleCommitment(item.id)">
            <div class="toggle-pip" />
          </div>
          <div class="rail-info">
            <span class="rail-name">{{ item.name }}</span>
            <span class="rail-freq">{{ item.frequency }}</span>
          </div>
          <div class="rail-amt pos">
            <input
              class="amt-input"
              :value="formatAmountDisplay(item)"
              @focus="onFocus($event, item)"
              @blur="onBlur($event, item)"
              @keydown.enter="($event.target as HTMLInputElement).blur()"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Expenses -->
    <div v-if="expenseItems.length">
      <div class="sec-hdr">
        <span class="sec-title">Expenses ({{ expenseItems.length }})</span>
        <span class="sec-total expense">{{ formatSigned(scenarioExpenses) }}/mo</span>
      </div>
      <div class="rail-list">
        <div
          v-for="item in expenseItems"
          :key="item.id"
          class="rail"
          :class="{ off: !isActive(item.id), modified: isModified(item.id) }"
          :style="{ '--weight': weight(item) + '%' }"
        >
          <div class="rail-toggle" @click="toggleCommitment(item.id)">
            <div class="toggle-pip" />
          </div>
          <div class="rail-info">
            <span class="rail-name">{{ item.name }}</span>
            <span class="rail-freq">{{ item.frequency }}</span>
          </div>
          <div class="rail-amt neg">
            <input
              class="amt-input"
              :value="formatAmountDisplay(item)"
              @focus="onFocus($event, item)"
              @blur="onBlur($event, item)"
              @keydown.enter="($event.target as HTMLInputElement).blur()"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- One-time -->
    <div v-if="oneTimeItems.length">
      <div class="sec-hdr">
        <span class="sec-title">One-Time ({{ oneTimeItems.length }})</span>
        <span class="sec-total dim">{{ formatSigned(oneTimeTotal) }}</span>
      </div>
      <div class="rail-list">
        <div
          v-for="item in oneTimeItems"
          :key="item.id"
          class="rail"
          :class="{ off: !isActive(item.id), modified: isModified(item.id) }"
          :style="{ '--weight': weight(item) + '%' }"
        >
          <div class="rail-toggle" @click="toggleCommitment(item.id)">
            <div class="toggle-pip" />
          </div>
          <div class="rail-info">
            <span class="rail-name">{{ item.name }}</span>
            <span class="rail-freq once">{{ item.one_time_date ?? 'once' }}</span>
          </div>
          <div class="rail-amt" :class="parseMoney(item.amount) >= 0 ? 'pos' : 'neg'">
            <input
              class="amt-input"
              :value="formatAmountDisplay(item)"
              @focus="onFocus($event, item)"
              @blur="onBlur($event, item)"
              @keydown.enter="($event.target as HTMLInputElement).blur()"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { CommitmentResponse } from '@/types/commitment'
import type { ScenarioOverride } from '@/composables/useScenario'
import { parseMoney, formatDollars } from '@/utils/format'

const props = defineProps<{
  commitments: CommitmentResponse[]
  overrides: Map<number, ScenarioOverride>
  scenarioIncome: number
  scenarioExpenses: number
}>()

const emit = defineEmits<{
  toggle: [id: number]
  amountChange: [id: number, amount: number]
}>()

function toggleCommitment(id: number) {
  emit('toggle', id)
}

// ── Grouping ──

const incomeItems = computed(() =>
  props.commitments.filter(
    commitment => parseMoney(commitment.amount) > 0 && commitment.frequency !== 'once',
  ),
)

const expenseItems = computed(() =>
  props.commitments.filter(
    commitment => parseMoney(commitment.amount) < 0 && commitment.frequency !== 'once',
  ),
)

const oneTimeItems = computed(() =>
  props.commitments.filter(commitment => commitment.frequency === 'once'),
)

const oneTimeTotal = computed(() =>
  oneTimeItems.value
    .filter(commitment => props.overrides.get(commitment.id)?.active !== false)
    .reduce((sum, commitment) => {
      const override = props.overrides.get(commitment.id)
      return sum + (override?.amount ?? parseMoney(commitment.amount))
    }, 0),
)

// ── Override helpers ──

function isActive(id: number): boolean {
  return props.overrides.get(id)?.active !== false
}

function isModified(id: number): boolean {
  return props.overrides.get(id)?.amount != null
}

function effectiveAmount(commitment: CommitmentResponse): number {
  const override = props.overrides.get(commitment.id)
  if (override?.amount != null) return override.amount
  return parseMoney(commitment.amount)
}

// ── Weight fill (proportion of max expense for visual bar) ──

const maxAbsAmount = computed(() =>
  Math.max(
    ...props.commitments.map(commitment => Math.abs(effectiveAmount(commitment))),
    1,
  ),
)

function weight(commitment: CommitmentResponse): number {
  return Math.round((Math.abs(effectiveAmount(commitment)) / maxAbsAmount.value) * 100)
}

// ── Amount display & editing ──

function formatAmountDisplay(commitment: CommitmentResponse): string {
  const amt = effectiveAmount(commitment)
  const sign = amt >= 0 ? '+' : '-'
  return `${sign}${formatDollars(amt)}`
}

function formatSigned(value: number): string {
  const sign = value >= 0 ? '+' : '-'
  return `${sign}${formatDollars(value)}`
}

function onFocus(event: Event, _commitment: CommitmentResponse) {
  const input = event.target as HTMLInputElement
  // Strip formatting — show raw number for editing.
  const raw = input.value.replace(/[^0-9.-]/g, '')
  input.value = raw
  input.select()
}

function onBlur(event: Event, commitment: CommitmentResponse) {
  const input = event.target as HTMLInputElement
  const raw = input.value.replace(/[^0-9.-]/g, '')
  const parsed = Number(raw)

  if (!Number.isNaN(parsed) && raw.length > 0) {
    // Maintain original sign: expenses are negative, income positive.
    const originalAmt = parseMoney(commitment.amount)
    const signed = originalAmt < 0 ? -Math.abs(parsed) : Math.abs(parsed)
    emit('amountChange', commitment.id, signed)
  }

  // Re-format display value.
  input.value = formatAmountDisplay(commitment)
}
</script>

<style scoped>
.rails-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sec-hdr {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.sec-title {
  font-size: 10px;
  font-weight: 700;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.sec-total {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 700;
}

.sec-total.income { color: var(--income); }
.sec-total.expense { color: var(--danger); }
.sec-total.dim { color: var(--dim); }

/* ── Rail list ── */

.rail-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* ── Rail row ── */

.rail {
  display: grid;
  grid-template-columns: 36px 1fr auto;
  align-items: center;
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  position: relative;
  overflow: hidden;
  transition: opacity 0.25s, border-color 0.2s;
}

/* Weight fill bar behind the row. */
.rail::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: var(--weight, 0%);
  background: rgba(255, 255, 255, 0.015);
  pointer-events: none;
  transition: width 0.3s;
}

.rail.off {
  opacity: 0.3;
}

.rail.off .rail-name {
  text-decoration: line-through;
  text-decoration-color: var(--dim);
}

/* Modified accent edge. */
.rail.modified {
  border-left: 2px solid var(--tight);
}

/* ── Toggle zone ── */

.rail-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 10px 0;
  cursor: pointer;
  position: relative;
  z-index: 1;
}

.toggle-pip {
  width: 8px;
  height: 8px;
  border: 1px solid var(--dim);
  transition: all 0.2s;
}

.rail:not(.off) .toggle-pip {
  background: var(--safe);
  border-color: var(--safe);
  box-shadow: 0 0 6px rgba(52, 211, 153, 0.3);
}

/* ── Name + freq ── */

.rail-info {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 10px 12px;
  position: relative;
  z-index: 1;
}

.rail-name {
  font-size: 12px;
  color: var(--text);
  font-weight: 500;
}

.rail-freq {
  font-size: 8px;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
}

/* ── Amount input ── */

.rail-amt {
  padding: 0 14px 0 0;
  position: relative;
  z-index: 1;
}

.amt-input {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  padding: 5px 8px;
  width: 100px;
  text-align: right;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: inherit;
  outline: none;
  transition: border-color 0.15s, background 0.15s;
}

.amt-input:hover {
  border-color: rgba(255, 255, 255, 0.08);
}

.amt-input:focus {
  border-color: rgba(167, 139, 250, 0.3);
  background: rgba(167, 139, 250, 0.04);
}

.rail-amt.neg { color: var(--danger); }
.rail-amt.pos { color: var(--income); }
</style>
