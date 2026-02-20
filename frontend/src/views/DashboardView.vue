<template>
  <div>
    <div class="wrap">
      <DashboardHero
        v-if="!loading && trajectory.length"
        :current-balance="currentBalance"
        :end-balance="endBalance"
        :net-change="netChange"
        :lowest-balance="lowestPoint?.balance ?? 0"
        :lowest-date="lowestPoint?.date ?? ''"
        :days-covered="daysCovered"
        @update-balance="onUpdateBalance"
      />

        <div class="sh" data-tour="bills" style="margin-top: 20px">
          <span class="sh-t">Bills This Week</span>
          <span class="sh-m">resets {{ nextWeekLabel }}</span>
        </div>
        <BillsThisWeek
          :bills="billsAnalysis.bills"
          :next-bills="billsAnalysis.nextBills"
        />

      <div v-if="loading" class="loading">Loading projection...</div>
      <div v-else-if="error" class="error-msg">{{ error }}</div>

      <template v-else-if="trajectory.length">
        <TrajectoryChart
          ref="chartRef"
          data-tour="trajectory"
          :data="trajectory"
          :highlight-date="highlightDate"
          :pulse-date="pulseDate"
          :highlighted-cause="highlightedCause"
          :worst-window="worstWindow"
          :expense-wave="expenseWave"
          :daily-expense-stack="dailyExpenseStack"
          :master-expense-order="masterExpenseOrder"
          :master-color-map="masterColorMap"
        />

        <ShortfallWarning :shortfall="shortfall" />

        <CausePanel
          data-tour="cause-panel"
          :worst-window="worstWindow"
          @highlight-cause="highlightedCause = $event"
        />

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
import { ref, computed, nextTick } from 'vue'
import DashboardHero from '@/components/DashboardHero.vue'
import TrajectoryChart from '@/components/TrajectoryChart.vue'
import EventList from '@/components/EventList.vue'
import CausePanel from '@/components/CausePanel.vue'
import BillsThisWeek from '@/components/BillsThisWeek.vue'
import ShortfallWarning from '@/components/ShortfallWarning.vue'
import { useDashboard } from '@/composables/useDashboard'
import { useExpenseAnalysis } from '@/composables/useExpenseAnalysis'
import { useTour } from '@/composables/useTour'
import { createManualBalance } from '@/api/balance'
import { parseLocalDate } from '@/utils/format'

const highlightDate = ref<string | null>(null)
const pulseDate = ref<string | null>(null)
const highlightedCause = ref<number | null>(null)
const chartRef = ref<InstanceType<typeof TrajectoryChart> | null>(null)

useTour()

function onClickDate(date: string) {
  pulseDate.value = null
  chartRef.value?.zoomToDate(date)
  nextTick(() => { pulseDate.value = date })
}

async function onUpdateBalance(balance: number) {
  try {
    await createManualBalance({
      balance: balance.toString(),
      observed_at: new Date().toISOString(),
      account_label: null,
    })
    await refresh()
  } catch (err) {
    console.error('Failed to update balance:', err)
  }
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
  refresh,
} = useDashboard()

const {
  worstWindow,
  expenseWave,
  dailyExpenseStack,
  masterExpenseOrder,
  masterColorMap,
  billsAnalysis,
  shortfall,
} = useExpenseAnalysis(trajectory, currentBalance)

const nextWeekLabel = computed(() => {
  const start = billsAnalysis.value.nextWeekStart
  if (!start) return ''
  return parseLocalDate(start).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
})
</script>

<style scoped>
.wrap {
  max-width: 1060px;
  margin: 0 auto;
  padding: 0 24px 40px;
}

.sh {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin: 28px 0 12px;
  gap: 12px;
}

.sh-t {
  font-size: 10px;
  font-weight: 700;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.sh-m {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted);
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
