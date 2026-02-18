<template>
  <section class="bands">
    <div class="band-row" v-for="period in payPeriods" :key="period.start_date + period.end_date">
      <div class="band-title">
        <strong>{{ formatRange(period.start_date, period.end_date) }}</strong>
        <span>
          Spent {{ formatCurrency(period.spent) }} • Min {{ formatCurrency(period.min_balance) }}
          <em v-if="period.is_partial">(partial)</em>
        </span>
      </div>
      <div class="band">
        <span class="stat">Start <strong>{{ formatCurrency(period.start_balance) }}</strong></span>
        <span class="stat">End <strong>{{ formatCurrency(period.end_balance) }}</strong></span>
        <span class="stat">Net <strong>{{ formatSigned(period.net) }}</strong></span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ParsedPayPeriod } from '@/types/projection'
import { formatCurrency, formatSigned, parseLocalDate } from '@/utils/format'

defineProps<{ payPeriods: ParsedPayPeriod[] }>()

const formatRange = (start: string, end: string) => {
  const s = parseLocalDate(start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  const e = parseLocalDate(end).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  return `${s} → ${e}`
}
</script>

<style scoped>
.bands {
  margin-top: 28px;
  background: var(--panel);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 0;
  padding: 22px;
  position: relative;
  overflow: hidden;
}

.bands::before {
  content: "";
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(90deg, transparent, transparent 120px, var(--grid) 120px, var(--grid) 121px);
  pointer-events: none;
}

.band-row {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 18px;
  padding: 14px 0;
  position: relative;
  z-index: 1;
}

.band-row + .band-row {
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.band-title {
  font-size: 13px;
  color: var(--muted);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.band-title strong {
  color: var(--ink);
  font-size: 15px;
}

.band-title em {
  font-style: normal;
  color: var(--warn);
  margin-left: 6px;
}

.band {
  position: relative;
  height: 44px;
  border-radius: 0;
  background: linear-gradient(90deg, rgba(110, 231, 255, 0.15), rgba(155, 123, 255, 0.08));
  border: 1px solid rgba(110, 231, 255, 0.2);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.03);
  display: flex;
  align-items: center;
  padding: 0 12px;
  gap: 12px;
}

.band .stat {
  font-size: 12px;
  color: var(--muted);
}

.band .stat strong {
  color: var(--ink);
  font-weight: 600;
}
</style>
