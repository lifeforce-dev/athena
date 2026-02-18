<template>
  <div>
    <nav class="nav-placeholder" />

    <div class="wrap">
      <div class="page-title">Commitments</div>
      <div class="page-sub">Manage recurring expenses, income, and one-time payments that drive your trajectory.</div>

      <!-- Summary cards -->
      <div class="summary">
        <div class="sum-card">
          <div class="sum-val" style="color: var(--income)">{{ fmtInt(totalMonthlyIncome) }}</div>
          <div class="sum-lbl">Monthly Income</div>
        </div>
        <div class="sum-card">
          <div class="sum-val" style="color: var(--danger)">{{ fmtInt(totalMonthlyExpenses) }}</div>
          <div class="sum-lbl">Monthly Expenses</div>
        </div>
        <div class="sum-card">
          <div class="sum-val" :style="{ color: netMonthly >= 0 ? 'var(--safe)' : 'var(--danger)' }">
            {{ netMonthly >= 0 ? '+' : '-' }}{{ fmtInt(netMonthly) }}
          </div>
          <div class="sum-lbl">Net / Month</div>
        </div>
        <div class="sum-card">
          <div class="sum-val" style="color: var(--bright)">{{ commitments.length }}</div>
          <div class="sum-lbl">Total Items</div>
        </div>
      </div>

      <!-- Add buttons -->
      <div class="add-bar">
        <button class="add-btn" @click="openAdd">
          <span class="plus">+</span> Add Commitment
        </button>
      </div>

      <!-- Loading / error states -->
      <div v-if="loading" class="empty-state">Loading commitments...</div>
      <div v-else-if="error" class="empty-state" style="color: var(--danger)">{{ error }}</div>

      <!-- Grouped commitment list -->
      <template v-else>
        <div v-for="group in groupedCommitments" :key="group.label" class="cat-box">
          <div class="cat-hdr">
            <span class="cat-name">{{ group.label }} ({{ group.items.length }})</span>
            <span class="cat-total" :class="{ pos: group.total > 0 }">
              {{ group.total > 0 ? '+' : '-' }}{{ fmtInt(group.total) }}/mo
            </span>
          </div>
          <div class="col-hdr">
            <span>Name</span>
            <span style="text-align: right">Amount</span>
            <span style="text-align: center">Frequency</span>
            <span style="text-align: center">Next</span>
            <span></span>
          </div>
          <div v-for="item in group.items" :key="item.id" class="c-row">
            <span class="c-name">
              {{ item.name }}
            </span>
            <span class="c-amt" :class="item.parsedAmount > 0 ? 'pos' : 'neg'">
              {{ item.parsedAmount > 0 ? '+' : '-' }}{{ fmtDollar(item.parsedAmount) }}
            </span>
            <span class="c-freq">{{ freqLabel(item.frequency) }}</span>
            <span class="c-next">{{ '-' }}</span>
            <button class="c-del" @click="handleDelete(item.id)" title="Remove">&times;</button>
          </div>
        </div>

        <!-- One-time payments -->
        <div v-if="oneTimeItems.length" class="cat-box">
          <div class="cat-hdr">
            <span class="cat-name">One-Time Payments ({{ oneTimeItems.length }})</span>
            <span class="cat-total">
              {{ fmtInt(oneTimeTotal) }} total
            </span>
          </div>
          <div class="col-hdr ot-hdr">
            <span>Date</span>
            <span>Name</span>
            <span style="text-align: right">Amount</span>
            <span></span>
          </div>
          <div v-for="item in oneTimeItems" :key="item.id" class="c-row ot-row">
            <span class="c-date">{{ fmtDate(item.one_time_date ?? item.start_date) }}</span>
            <span class="c-name">{{ item.name }}</span>
            <span class="c-amt" :class="item.parsedAmount > 0 ? 'pos' : 'neg'">
              {{ item.parsedAmount > 0 ? '+' : '-' }}{{ fmtDollar(item.parsedAmount) }}
            </span>
            <button class="c-del" @click="handleDelete(item.id)" title="Remove">&times;</button>
          </div>
        </div>
      </template>
    </div>

    <CommitmentModal
      :visible="modalOpen"
      :edit-data="editTarget"
      @close="modalOpen = false"
      @save="handleSave"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import CommitmentModal from '@/components/CommitmentModal.vue'
import { useCommitments } from '@/composables/useCommitments'
import type { CommitmentCreate } from '@/types/commitment'
import { parseMoney, parseLocalDate } from '@/utils/format'

const {
  commitments,
  loading,
  error,
  parsed,
  totalMonthlyIncome,
  totalMonthlyExpenses,
  netMonthly,
  create,
  update,
  remove,
} = useCommitments()

const modalOpen = ref(false)
const editTarget = ref<any>(null)

const fmtInt = (n: number) =>
  '$' + Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })

const fmtDollar = (n: number) =>
  '$' + Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const freqLabel = (f: string) => {
  const labels: Record<string, string> = {
    monthly: 'Monthly',
    biweekly: 'Biweekly',
    weekly: 'Weekly',
    daily: 'Daily',
    day_interval: 'Custom',
    once: 'One-Time',
  }
  return labels[f] ?? f
}

function monthlyEquiv(amount: number, freq: string, intervalDays?: number | null): number {
  if (freq === 'day_interval' && intervalDays) {
    return amount * (30.44 / intervalDays)
  }
  const multipliers: Record<string, number> = {
    monthly: 1,
    biweekly: 26 / 12,
    weekly: 52 / 12,
    daily: 365.25 / 12,
    once: 0,
  }
  return amount * (multipliers[freq] ?? 1)
}

interface GroupedCategory {
  label: string
  items: typeof parsed.value
  total: number
}

const groupedCommitments = computed<GroupedCategory[]>(() => {
  const income = parsed.value.filter(c => parseMoney(c.amount) > 0 && c.frequency !== 'once')
  const expenses = parsed.value.filter(c => parseMoney(c.amount) < 0 && c.frequency !== 'once')
  const oneTime = parsed.value.filter(c => c.frequency === 'once')

  const groups: GroupedCategory[] = []

  if (income.length) {
    groups.push({
      label: 'Income',
      items: income.sort((a, b) => Math.abs(b.parsedAmount) - Math.abs(a.parsedAmount)),
      total: income.reduce((s, c) => s + monthlyEquiv(c.parsedAmount, c.frequency, c.interval_days), 0),
    })
  }

  if (expenses.length) {
    groups.push({
      label: 'Expenses',
      items: expenses.sort((a, b) => Math.abs(b.parsedAmount) - Math.abs(a.parsedAmount)),
      total: expenses.reduce((s, c) => s + monthlyEquiv(c.parsedAmount, c.frequency), 0),
    })
  }

  return groups
})

const oneTimeItems = computed(() =>
  parsed.value
    .filter(c => c.frequency === 'once')
    .sort((a, b) => (a.one_time_date ?? a.start_date).localeCompare(b.one_time_date ?? b.start_date))
)

const oneTimeTotal = computed(() =>
  oneTimeItems.value.reduce((s, c) => s + Math.abs(c.parsedAmount), 0)
)

const fmtDate = (d: string) =>
  parseLocalDate(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })

function openAdd() {
  editTarget.value = null
  modalOpen.value = true
}

async function handleSave(data: CommitmentCreate, editId?: number) {
  if (editId) {
    await update(editId, data)
  } else {
    await create(data)
  }
  modalOpen.value = false
}

async function handleDelete(id: number) {
  await remove(id)
}
</script>

<style scoped>
.nav-placeholder {
  /* NavBar is in App.vue; this just provides consistent spacing. */
}

.wrap {
  max-width: 900px;
  margin: 0 auto;
  padding: 32px 24px 48px;
}

.page-title {
  font-size: 20px;
  font-weight: 800;
  color: var(--bright);
  margin-bottom: 4px;
}

.page-sub {
  font-size: 12px;
  color: var(--dim);
  margin-bottom: 28px;
}

/* Summary cards */
.summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 28px;
}

.sum-card {
  backdrop-filter: blur(16px);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
  text-align: center;
  box-shadow: var(--shadow-sm);
}

.sum-val {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 700;
}

.sum-lbl {
  font-size: 8px;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: 4px;
  font-weight: 700;
}

/* Add bar */
.add-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 28px;
}

.add-btn {
  backdrop-filter: blur(16px);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 0;
  padding: 10px 20px;
  color: var(--bright);
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.add-btn:hover {
  background: var(--raised);
  border-color: rgba(255, 255, 255, 0.1);
}

.add-btn .plus {
  color: var(--income);
  font-size: 16px;
  font-weight: 400;
}

/* Category boxes */
.cat-box {
  backdrop-filter: blur(16px);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: 16px;
  box-shadow: var(--shadow-card);
}

.cat-hdr {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  background: var(--raised);
  border-bottom: 1px solid var(--border);
}

.cat-name {
  font-size: 10px;
  font-weight: 700;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.cat-total {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  color: var(--danger);
}

.cat-total.pos {
  color: var(--income);
}

.col-hdr {
  display: grid;
  grid-template-columns: 1fr 90px 90px 90px 40px;
  gap: 10px;
  padding: 8px 18px;
  border-bottom: 1px solid var(--border);
  font-size: 8px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.c-row {
  display: grid;
  grid-template-columns: 1fr 90px 90px 90px 40px;
  gap: 10px;
  align-items: center;
  padding: 8px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.02);
  transition: background 0.12s;
}

.c-row:last-child { border-bottom: none; }
.c-row:hover { background: rgba(255, 255, 255, 0.02); }

.c-name {
  font-size: 12px;
  color: var(--text);
  font-weight: 500;
}

.c-amt {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  text-align: right;
}

.c-amt.neg { color: var(--danger); }
.c-amt.pos { color: var(--income); }

.c-freq {
  font-size: 10px;
  color: var(--dim);
  text-align: center;
}

.c-next {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--dim);
  text-align: center;
}

.c-del {
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  color: var(--muted);
  cursor: pointer;
  font-size: 14px;
  border-radius: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.c-del:hover {
  background: rgba(248, 113, 113, 0.1);
  color: var(--danger);
}

.once-tag {
  display: inline-block;
  font-size: 8px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 2px 6px;
  border-radius: 0;
  background: rgba(167, 139, 250, 0.1);
  color: var(--income);
  margin-left: 8px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--dim);
}

.ot-hdr, .ot-row {
  grid-template-columns: 100px 1fr 90px 40px;
}

.c-date {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--dim);
}

@media (max-width: 700px) {
  .summary { grid-template-columns: 1fr 1fr; }
  .col-hdr, .c-row { grid-template-columns: 1fr 70px 70px 30px; }
  .ot-hdr, .ot-row { grid-template-columns: 80px 1fr 70px 30px; }
  .c-next, .col-hdr > span:nth-child(4) { display: none; }
}
</style>
