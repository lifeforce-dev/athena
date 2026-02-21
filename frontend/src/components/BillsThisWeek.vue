<template>
  <div class="btw-panel">
    <template v-if="bills.length === 0">
      <div class="btw-empty">{{ t('bills.empty') }}</div>
    </template>
    <template v-else>
      <div v-for="bill in bills" :key="bill.name + bill.date" class="btw-row">
        <span class="btw-day">{{ weekday(bill.date) }}</span>
        <span class="btw-name">{{ bill.name }}</span>
        <span class="btw-amt">-{{ formatDollars(bill.amount) }}</span>
      </div>
      <div class="btw-total">
        <span>{{ t('bills.total') }}</span>
        <span>-{{ formatDollars(thisWeekTotal) }}</span>
      </div>
    </template>

    <template v-if="nextBills.length > 0">
      <div class="btw-next-label">{{ t('bills.next_week', { amount: formatDollars(nextWeekTotal) }) }}</div>
      <div v-for="bill in nextBills" :key="bill.name + bill.date" class="btw-row btw-next">
        <span class="btw-day">{{ weekday(bill.date) }}</span>
        <span class="btw-name">{{ bill.name }}</span>
        <span class="btw-amt">-{{ formatDollars(bill.amount) }}</span>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { BillEntry } from '@/composables/useExpenseAnalysis'
import { parseLocalDate, formatDollars } from '@/utils/format'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps<{
  bills: BillEntry[]
  nextBills: BillEntry[]
}>()

const weekday = (dateStr: string) =>
  parseLocalDate(dateStr).toLocaleDateString('en-US', { weekday: 'short' })

const thisWeekTotal = computed(() =>
  props.bills.reduce((total, bill) => total + bill.amount, 0)
)

const nextWeekTotal = computed(() =>
  props.nextBills.reduce((total, bill) => total + bill.amount, 0)
)
</script>

<style scoped>
.btw-panel {
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 14px 16px;
}

.btw-empty {
  font-size: 12px;
  color: var(--safe);
  padding: 2px 0;
}

.btw-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
  font-size: 11px;
}

.btw-day {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--dim);
  width: 28px;
  flex-shrink: 0;
}

.btw-name {
  flex: 1;
  color: var(--text);
}

.btw-amt {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--danger);
}

.btw-total {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid var(--border);
  margin-top: 6px;
  padding-top: 6px;
  font-size: 11px;
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--danger);
}

.btw-next-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--dim);
  margin-top: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
  letter-spacing: 0.3px;
  margin-bottom: 4px;
}

.btw-row.btw-next {
  opacity: 0.5;
}
</style>
