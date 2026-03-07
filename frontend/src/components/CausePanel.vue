<template>
  <div v-if="worstWindow" class="cause-panel">
    <div class="cause-header">
      <div class="cause-title">{{ t('cause.title') }}</div>
      <div class="cause-window">
        {{ windowRange }} | {{ t('cause.total', { amount: formatDollars(worstWindow.totalExpenses) }) }}
      </div>
    </div>

    <div class="cause-bar-wrap">
      <div class="cause-bar">
        <div
          v-for="(exp, i) in worstWindow.expenses"
          :key="exp.name"
          class="cause-bar-seg"
          :class="{ dimmed: highlightIdx !== null && highlightIdx !== i }"
          :style="{
            width: segWidth(exp.amount) + '%',
            background: color(i),
          }"
          @mouseenter="onHighlight(i)"
          @mouseleave="onHighlight(null)"
        >
          {{ segWidth(exp.amount) > 8 ? exp.name : '' }}
        </div>
      </div>
    </div>

    <div class="cause-list">
      <div
        v-for="(exp, i) in worstWindow.expenses"
        :key="exp.name"
        class="cause-row"
        :class="{ highlighted: highlightIdx === i }"
        @mouseenter="onHighlight(i)"
        @mouseleave="onHighlight(null)"
      >
        <div class="cause-dot" :style="{ background: color(i) }" />
        <div class="cause-name">
          {{ exp.name }}
          <span class="cause-date">{{ shortDate(exp.date) }}</span>
        </div>
        <div class="cause-amt">-{{ formatDollars(exp.amount) }}</div>
        <div class="cause-pct">{{ percentOfTotal(exp.amount) }}%</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { WorstWindow } from '@/composables/useExpenseAnalysis'
import { CAUSE_COLORS } from '@/composables/useExpenseAnalysis'
import { parseLocalDate, formatDollars, getDateLocale } from '@/utils/format'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps<{
  worstWindow: WorstWindow | null
}>()

const emit = defineEmits<{
  highlightCause: [index: number | null]
}>()

const highlightIdx = ref<number | null>(null)

function onHighlight(idx: number | null) {
  highlightIdx.value = idx
  emit('highlightCause', idx)
}

const shortDate = (dateStr: string) =>
  parseLocalDate(dateStr).toLocaleDateString(getDateLocale(), { month: 'short', day: 'numeric' })

const windowRange = computed(() => {
  if (!props.worstWindow) return ''
  const range = `${shortDate(props.worstWindow.startDate)} - ${shortDate(props.worstWindow.endDate)}`
  return t('cause.window_range', { range })
})

function segWidth(amount: number) {
  if (!props.worstWindow || !props.worstWindow.totalExpenses) return 0
  return (amount / props.worstWindow.totalExpenses) * 100
}

function percentOfTotal(amount: number) {
  if (!props.worstWindow || !props.worstWindow.totalExpenses) return 0
  return Math.round((amount / props.worstWindow.totalExpenses) * 100)
}

function color(i: number) {
  return CAUSE_COLORS[i % CAUSE_COLORS.length]
}
</script>

<style scoped>
.cause-panel {
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 20px;
  margin-top: 16px;
}

.cause-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.cause-title {
  font-weight: 700;
  font-size: 13px;
  color: var(--bright);
}

.cause-window {
  font-size: 10px;
  color: var(--dim);
  font-family: var(--font-mono);
}

.cause-bar-wrap {
  margin-bottom: 16px;
}

.cause-bar {
  height: 28px;
  background: rgba(255, 255, 255, 0.03);
  display: flex;
  overflow: hidden;
  position: relative;
}

.cause-bar-seg {
  height: 100%;
  transition: opacity 0.15s;
  cursor: pointer;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 8px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.5);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  padding: 0 4px;
}

.cause-bar-seg:hover {
  opacity: 1 !important;
}

.cause-bar-seg.dimmed {
  opacity: 0.4;
}

.cause-list {
  display: grid;
  gap: 6px;
}

.cause-row {
  display: grid;
  grid-template-columns: 8px 1fr 60px 50px;
  gap: 10px;
  align-items: center;
  padding: 6px 8px;
  cursor: pointer;
  transition: background 0.1s;
}

.cause-row:hover {
  background: rgba(255, 255, 255, 0.03);
}

.cause-row.highlighted {
  background: rgba(255, 255, 255, 0.04);
}

.cause-dot {
  width: 8px;
  height: 8px;
}

.cause-name {
  font-size: 11px;
  color: var(--text);
}

.cause-date {
  font-size: 9px;
  color: var(--dim);
}

.cause-amt {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 11px;
  color: var(--danger);
  text-align: right;
}

.cause-pct {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--dim);
  text-align: right;
}
</style>
