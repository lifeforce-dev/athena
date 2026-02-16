<template>
  <div class="page">
    <header class="header">
      <div>
        <h1>Cash Pulse</h1>
        <p class="subtitle">Paycheck intervals, rent pressure, and at-a-glance risk.</p>
      </div>
      <div class="controls">
        <label>
          From
          <input type="date" v-model="fromDate" />
        </label>
        <label>
          As of
          <input type="date" v-model="asOf" />
        </label>
        <button @click="refresh" :disabled="loading">Refresh</button>
      </div>
    </header>

    <section class="summary">
      <div class="card">
        <div class="label">Current Balance</div>
        <div class="value">{{ formatCurrency(currentBalance) }}</div>
        <div class="pill" v-if="currentBalance >= 0">Projected</div>
      </div>
      <div class="card">
        <div class="label">Next Check</div>
        <div class="value">{{ nextCheckLabel }}</div>
        <div class="pill">Inflow {{ formatCurrency(nextCheckAmount) }}</div>
      </div>
      <div class="card">
        <div class="label">Rent Risk</div>
        <div class="value">{{ rentRisk.label }}</div>
        <div class="pill" :class="{ warn: rentRisk.level === 'warn' }">
          {{ rentRisk.detail }}
        </div>
      </div>
    </section>

    <PaycheckBands :payPeriods="payPeriods" />

    <section class="ledger">
      <h3>Upcoming Outflows</h3>
      <div class="row" v-for="item in upcomingOutflows" :key="item.date + item.name">
        <div>{{ shortDate(item.date) }}</div>
        <div>{{ item.name }}</div>
        <div class="amt">{{ formatSigned(item.delta) }}</div>
      </div>
    </section>

    <div class="error" v-if="error">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import PaycheckBands from '@/components/PaycheckBands.vue'
import { useProjection } from '@/composables/useProjection'
import { formatCurrency, formatSigned, parseLocalDate, toLocalDateString } from '@/utils/format'

const { data, load, loading, error, currentBalance, payPeriods, ledger } = useProjection()

const today = new Date()
const threeMonthsOut = new Date(today.getFullYear(), today.getMonth() + 3, today.getDate())

const fromDate = ref(toLocalDateString(today))
const asOf = ref(toLocalDateString(threeMonthsOut))

const refresh = () => load(asOf.value, fromDate.value)

onMounted(refresh)

const nextCheckLabel = computed(() => {
  if (!data.value) return '--'
  const todayStr = toLocalDateString(new Date())
  const nextInflow = data.value.ledger.find(
    (entry) => entry.delta > 0 && entry.date >= todayStr
  )
  return nextInflow ? shortDate(nextInflow.date) : '--'
})

const nextCheckAmount = computed(() => {
  if (!data.value) return 0
  const todayStr = toLocalDateString(new Date())
  // First future inflow in the ledger (YYYY-MM-DD strings are safe for lexicographic ordering)
  const nextInflow = data.value.ledger.find(
    (entry) => entry.delta > 0 && entry.date >= todayStr
  )
  return nextInflow?.delta ?? 0
})

const todayAnchor = computed(() => toLocalDateString(new Date()))

const rentRisk = computed(() => {
  const rentEntry = ledger.value.find(
    (entry) => entry.name.toLowerCase().includes('rent') && entry.date >= todayAnchor.value
  )
  if (!rentEntry) {
    return { label: 'Unknown', detail: 'Rent not found', level: 'ok' as const }
  }
  const rentDate = rentEntry.date
  // ISO YYYY-MM-DD strings sort lexicographically, matching chronological order
  const period = payPeriods.value.find(
    (p) => rentDate >= p.start_date && rentDate <= p.end_date
  )
  if (!period) {
    return { label: 'Unknown', detail: 'No period match', level: 'ok' as const }
  }
  const level = period.min_balance >= Math.abs(rentEntry.delta) ? 'ok' : 'warn'
  const detail = `Min ${formatCurrency(period.min_balance)} vs Rent ${formatCurrency(Math.abs(rentEntry.delta))}`
  return { label: level === 'ok' ? 'Safe' : 'Tight', detail, level }
})

const upcomingOutflows = computed(() =>
  ledger.value.filter((item) => item.delta < 0 && item.date >= todayAnchor.value).slice(0, 8)
)

const shortDate = (value: string) =>
  parseLocalDate(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
</script>

<style scoped>
.page {
  max-width: 1200px;
  margin: 48px auto;
  padding: 0 24px 60px;
}

.header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: center;
}

.subtitle {
  color: var(--muted);
  margin: 6px 0 0;
  font-size: 14px;
}

.controls {
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--muted);
}

input {
  background: var(--panel);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  color: var(--ink);
  padding: 8px 10px;
}

button {
  background: linear-gradient(120deg, rgba(110, 231, 255, 0.2), rgba(155, 123, 255, 0.2));
  border: 1px solid rgba(110, 231, 255, 0.4);
  color: var(--ink);
  padding: 10px 16px;
  border-radius: 12px;
  cursor: pointer;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.summary {
  margin-top: 24px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.card {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01));
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.35);
}

.label {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1.2px;
}

.value {
  font-size: 26px;
  margin-top: 6px;
  font-weight: 600;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  margin-top: 8px;
  background: rgba(125, 255, 181, 0.1);
  color: var(--ok);
  border: 1px solid rgba(125, 255, 181, 0.25);
}

.pill.warn {
  background: rgba(255, 141, 141, 0.15);
  color: var(--warn);
  border-color: rgba(255, 141, 141, 0.3);
}

.ledger {
  margin-top: 28px;
  background: var(--panel-2);
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 16px 18px;
}

.ledger h3 {
  font-size: 20px;
  margin-bottom: 12px;
}

.row {
  display: grid;
  grid-template-columns: 120px 1fr 110px;
  gap: 12px;
  padding: 8px 0;
  border-top: 1px dashed rgba(255, 255, 255, 0.06);
  font-size: 13px;
}

.row:first-of-type {
  border-top: none;
}

.amt {
  text-align: right;
  font-weight: 600;
  color: var(--warn);
}

.error {
  margin-top: 16px;
  color: var(--warn);
}
</style>
