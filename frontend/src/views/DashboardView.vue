<template>
  <div>
    <DashboardHero
      v-if="!loading && trajectory.length"
      :current-balance="currentBalance"
      :end-balance="endBalance"
      :net-change="netChange"
      :lowest-balance="lowestPoint?.balance ?? 0"
      :lowest-date="lowestPoint?.date ?? ''"
      :days-covered="daysCovered"
    />

    <div class="wrap">
      <div v-if="loading" class="loading">Loading projection...</div>
      <div v-else-if="error" class="error-msg">{{ error }}</div>

      <template v-else-if="trajectory.length">
        <TrajectoryChart ref="chartRef" :data="trajectory" :highlight-date="highlightDate" :pulse-date="pulseDate" />
        <EventList :ledger="ledger" @hover-date="highlightDate = $event" @click-date="onClickDate" />
      </template>

      <div v-else class="empty">
        <h3>No projection data</h3>
        <p>Add commitments to see your cash flow trajectory.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import DashboardHero from '@/components/DashboardHero.vue'
import TrajectoryChart from '@/components/TrajectoryChart.vue'
import EventList from '@/components/EventList.vue'
import { useDashboard } from '@/composables/useDashboard'

const highlightDate = ref<string | null>(null)
const pulseDate = ref<string | null>(null)
const chartRef = ref<InstanceType<typeof TrajectoryChart> | null>(null)

function onClickDate(date: string) {
  pulseDate.value = null
  chartRef.value?.zoomToDate(date)
  // Set on next tick so the watch fires even if the same date is clicked again.
  nextTick(() => { pulseDate.value = date })
}

const {
  loading,
  error,
  trajectory,
  lowestPoint,
  currentBalance,
  endBalance,
  netChange,
  daysCovered,
  ledger,
} = useDashboard()
</script>

<style scoped>
.wrap {
  max-width: 1060px;
  margin: 0 auto;
  padding: 0 24px 40px;
}

.loading,
.error-msg,
.empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--dim);
}

.error-msg {
  color: var(--danger);
}

.empty h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}

.empty p {
  font-size: 12px;
  max-width: 400px;
  margin: 0 auto;
}
</style>
