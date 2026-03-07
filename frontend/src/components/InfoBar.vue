<template>
  <div class="info-bar" :style="{ gridTemplateColumns: gridCols }">
    <template v-if="hasData">
      <!-- Baseline: always shown -->
      <span class="info-col info-date">{{ dateStr }}</span>
      <div class="info-sep" />
      <span class="info-col info-bal" :style="{ color: balColor }">{{ balStr }}</span>

      <!-- Band overlay: bill name + closest occurrence date + amount -->
      <template v-if="data!.band">
        <div class="info-sep" />
        <span class="info-col info-name">{{ data!.band.name }}</span>
        <div class="info-sep" />
        <span class="info-col info-billdate">{{ billDateStr }}</span>
        <div class="info-sep" />
        <span class="info-col info-amt" style="color: var(--danger)">{{ bandAmtStr }}</span>
      </template>

      <!-- Event overlay: income/one-time near the trajectory line -->
      <template v-else-if="data!.event">
        <div class="info-sep" />
        <span class="info-col info-name">{{ data!.event.name }}</span>
        <div class="info-sep" />
        <span class="info-col info-amt" :style="{ color: eventAmtColor }">{{ eventAmtStr }}</span>
      </template>
    </template>
    <span v-else class="info-hint">{{ t('chart.hover_hint') }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatDollars, getDateLocale } from '@/utils/format'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

export interface InfoBarData {
  date: string
  dayOffset: number
  balance: number
  balanceZone: 'safe' | 'tight' | 'danger'
  // Band hover: expense band closest occurrence info.
  band?: {
    name: string
    occurrenceDate: string
    occurrenceDayOffset: number
    amount: number
  }
  // Event hover: income/one-time payment near trajectory line.
  event?: {
    name: string
    amount: number
    isIncome: boolean
  }
}

const props = defineProps<{
  data: InfoBarData | null
}>()

const hasData = computed(() => props.data !== null)

const gridCols = computed(() => {
  if (!props.data) return '1fr'
  if (props.data.band) return '160px 1px 100px 1px 140px 1px 120px 1px 80px'
  if (props.data.event) return '160px 1px 100px 1px 140px 1px 80px'
  return '160px 1px 100px'
})

const dateStr = computed(() => {
  if (!props.data) return ''
  const parsed = new Date(props.data.date + 'T12:00:00')
  const cal = parsed.toLocaleDateString(getDateLocale(), { weekday: 'short', month: 'short', day: 'numeric' })
  return `${cal} | +${props.data.dayOffset}d`
})

const balStr = computed(() => (props.data ? formatDollars(props.data.balance) : ''))

const balColor = computed(() => {
  if (!props.data) return ''
  const zone = props.data.balanceZone
  if (zone === 'danger') return 'var(--danger)'
  if (zone === 'tight') return 'var(--tight)'
  return 'var(--safe)'
})

// Band: closest occurrence date formatted.
const billDateStr = computed(() => {
  const band = props.data?.band
  if (!band) return ''
  const parsed = new Date(band.occurrenceDate + 'T12:00:00')
  const cal = parsed.toLocaleDateString(getDateLocale(), { month: 'short', day: 'numeric' })
  return `${cal} | +${band.occurrenceDayOffset}d`
})

const bandAmtStr = computed(() => {
  const band = props.data?.band
  if (!band) return ''
  return `-${formatDollars(band.amount)}`
})

// Event: income/one-time payment.
const eventAmtStr = computed(() => {
  const event = props.data?.event
  if (!event) return ''
  const sign = event.isIncome ? '+' : '-'
  return `${sign}${formatDollars(event.amount)}`
})

const eventAmtColor = computed(() => {
  const event = props.data?.event
  if (!event) return ''
  return event.isIncome ? 'var(--income)' : 'var(--danger)'
})
</script>

<style scoped>
.info-bar {
  display: grid;
  align-items: center;
  gap: 0;
  margin-bottom: 6px;
  padding: 6px 12px;
  background: var(--panel);
  border: 1px solid var(--border);
  height: 30px;
  font-size: 11px;
}

.info-col {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 0 8px;
}

.info-sep {
  width: 1px;
  align-self: stretch;
  background: var(--border);
}

.info-date {
  font-weight: 700;
  color: var(--bright);
}

.info-bal {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 13px;
}

.info-name {
  font-size: 11px;
  color: var(--dim);
}

.info-billdate {
  font-size: 10px;
  color: var(--muted);
  font-family: var(--font-mono);
}

.info-amt {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 11px;
}

.info-hint {
  font-size: 10px;
  color: var(--dim);
  font-style: italic;
  grid-column: 1 / -1;
  padding: 0 8px;
}
</style>
