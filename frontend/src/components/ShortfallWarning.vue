<template>
  <div class="shortfall" v-if="shortfall">
    <div class="shortfall-header">
      <span class="shortfall-icon">!</span>
      <div class="shortfall-headline">
        <span class="shortfall-title">
          {{ t('shortfall.goes_negative', { date: shortDate(shortfall.brokeDate) }) }}
        </span>
        <span class="shortfall-sub">
          {{ t('shortfall.projected', { amount: formatDollars(shortfall.brokeBalance) }) }}
          <template v-if="shortfall.recoveryDate">
            {{ t('shortfall.recovery', { date: shortDate(shortfall.recoveryDate) }) }}
          </template>
        </span>
      </div>
    </div>

    <div class="shortfall-bills">
      <div
        v-for="(item, i) in shortfall.missedCommitments"
        :key="i"
        class="shortfall-row"
      >
        <span class="shortfall-date">{{ shortDate(item.date) }}</span>
        <span class="shortfall-name">{{ item.name }}</span>
        <span class="shortfall-amt">-{{ formatDollars(item.amount) }}</span>
      </div>
    </div>

    <div class="shortfall-footer">
      <span>{{ t('shortfall.at_risk', { count: shortfall.missedCommitments.length }) }}</span>
      <span class="shortfall-total">{{ t('shortfall.total', { amount: formatDollars(shortfall.totalMissed) }) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Shortfall } from '@/composables/useExpenseAnalysis'
import { formatDollars, shortDate } from '@/utils/format'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

defineProps<{
  shortfall: Shortfall | null
}>()
</script>

<style scoped>
.shortfall {
  margin-top: 12px;
  border: 1px solid var(--danger);
  background: var(--danger-glow);
  padding: 0;
  overflow: hidden;
}

.shortfall-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(248, 113, 113, 0.08);
  border-bottom: 1px solid rgba(248, 113, 113, 0.15);
}

.shortfall-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: var(--danger);
  color: var(--bg);
  font-weight: 800;
  font-size: 13px;
  flex-shrink: 0;
}

.shortfall-headline {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.shortfall-title {
  font-weight: 700;
  font-size: 12px;
  color: var(--danger);
}

.shortfall-sub {
  font-size: 10px;
  color: var(--dim);
}

.shortfall-bills {
  padding: 6px 14px;
}

.shortfall-row {
  display: grid;
  grid-template-columns: 60px 1fr 80px;
  gap: 8px;
  padding: 4px 0;
  font-size: 11px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.shortfall-row:last-child {
  border-bottom: none;
}

.shortfall-date {
  color: var(--dim);
  font-size: 10px;
}

.shortfall-name {
  color: var(--bright);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.shortfall-amt {
  text-align: right;
  color: var(--danger);
  font-family: var(--font-mono);
  font-weight: 600;
}

.shortfall-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  border-top: 1px solid rgba(248, 113, 113, 0.15);
  font-size: 10px;
  color: var(--dim);
}

.shortfall-total {
  color: var(--danger);
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 11px;
}
</style>
