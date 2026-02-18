<template>
  <div class="info-bar">
    <template v-if="hasData">
      <span class="info-col info-date">{{ dateStr }}</span>
      <div class="info-sep" />
      <span class="info-col info-bal" :style="{ color: balColor }">{{ balStr }}</span>
      <div class="info-sep" />
      <span class="info-col info-name">{{ name }}</span>
      <div class="info-sep" />
      <span class="info-col info-amt" :style="{ color: amtColor }">{{ amtStr }}</span>
    </template>
    <span v-else class="info-hint">hover chart to inspect</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface InfoBarData {
  date: string
  dayOffset: number
  balance: number
  balanceZone: 'safe' | 'tight' | 'danger'
  name: string
  amount: number
  isIncome: boolean
}

const props = defineProps<{
  data: InfoBarData | null
}>()

const hasData = computed(() => props.data !== null)

const fmtShort = (n: number) =>
  '$' + Math.abs(Math.round(n)).toLocaleString()

const dateStr = computed(() => {
  if (!props.data) return ''
  const dt = new Date(props.data.date + 'T12:00:00')
  const cal = dt.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  return `${cal} | +${props.data.dayOffset}d`
})

const balStr = computed(() => (props.data ? fmtShort(props.data.balance) : ''))

const balColor = computed(() => {
  if (!props.data) return ''
  const zone = props.data.balanceZone
  if (zone === 'danger') return 'var(--danger)'
  if (zone === 'tight') return 'var(--tight)'
  return 'var(--safe)'
})

const name = computed(() => props.data?.name ?? '')

const amtStr = computed(() => {
  if (!props.data) return ''
  const sign = props.data.isIncome ? '+' : '-'
  return `${sign}${fmtShort(props.data.amount)}`
})

const amtColor = computed(() => {
  if (!props.data) return ''
  return props.data.isIncome ? 'var(--income)' : 'var(--danger)'
})
</script>

<style scoped>
.info-bar {
  display: grid;
  grid-template-columns: 160px 1px 100px 1px 140px 1px 80px;
  align-items: center;
  gap: 0;
  margin-bottom: 6px;
  padding: 6px 12px;
  background: var(--panel);
  border: 1px solid var(--border);
  min-height: 30px;
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
