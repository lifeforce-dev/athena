<template>
  <div>
    <div class="wrap">
      <DashboardHero
        v-if="!loading && (trajectory.length || hasInitialBalance)"
        :current-balance="currentBalance"
        :end-balance="endBalance"
        :net-change="netChange"
        :lowest-balance="riskAnalysis.lowestBalance"
        :lowest-date="riskAnalysis.lowestDate ?? ''"
        :risk-level="riskAnalysis.riskLevel"
        :critical-threshold="criticalThreshold"
        :tight-threshold="tightThreshold"
        :days-covered="daysCovered"
        :balance-only="hasInitialBalance && !trajectory.length"
        @update-balance="onUpdateBalance"
        @refreshed="refresh"
      />

        <div class="sh" data-tour="bills" style="margin-top: 20px">
          <span class="sh-t">{{ t('dash.bills_this_week') }}</span>
          <span class="sh-m">{{ t('dash.resets', { date: nextWeekLabel }) }}</span>
        </div>
        <BillsThisWeek
          :bills="billsAnalysis.bills"
          :next-bills="billsAnalysis.nextBills"
        />

      <div v-if="loading" class="loading">{{ t('dash.loading') }}</div>
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
          :backend-lowest-balance="riskAnalysis.lowestBalance"
          :backend-lowest-date="riskAnalysis.lowestDate"
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
        <h3>{{ t('dash.no_data_title') }}</h3>
        <p>{{ t('dash.no_data_desc') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import DashboardHero from '@/components/DashboardHero.vue'
import TrajectoryChart from '@/components/TrajectoryChart.vue'
import EventList from '@/components/EventList.vue'
import CausePanel from '@/components/CausePanel.vue'
import BillsThisWeek from '@/components/BillsThisWeek.vue'
import ShortfallWarning from '@/components/ShortfallWarning.vue'
import { useDashboard } from '@/composables/useDashboard'
import { useExpenseAnalysis } from '@/composables/useExpenseAnalysis'
import { useTabOnboarding } from '@/composables/useTabOnboarding'
import { useI18n } from '@/composables/useI18n'
import { useTellerStore } from '@/stores/teller'
import { useAuthStore } from '@/stores/auth'
import { createManualBalance } from '@/api/balance'
import { parseLocalDate, getDateLocale, parseMoney } from '@/utils/format'
const highlightDate = ref<string | null>(null)
const pulseDate = ref<string | null>(null)
const highlightedCause = ref<number | null>(null)
const chartRef = ref<InstanceType<typeof TrajectoryChart> | null>(null)

const { t } = useI18n()

useTabOnboarding({
  name: 'dashboard',
  steps: (t) => [
    { element: '[data-tour="balance"]', popover: { title: t('tour.balance_title'), description: t('tour.balance_desc') } },
    { element: '[data-tour="gauge"]', popover: { title: t('tour.gauge_title'), description: t('tour.gauge_desc') } },
    { element: '[data-tour="bills"]', popover: { title: t('tour.bills_title'), description: t('tour.bills_desc') } },
    { element: '[data-tour="trajectory"]', popover: { title: t('tour.trajectory_title'), description: t('tour.trajectory_desc') } },
    { element: '[data-tour="cause-panel"]', popover: { title: t('tour.cause_title'), description: t('tour.cause_desc') } },
    { element: '[data-tour="currency-toggle"]', popover: { title: t('tour.currency_title'), description: t('tour.currency_desc') } },
  ],
})

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
  riskAnalysis,
  currentBalance,
  hasInitialBalance,
  endBalance,
  netChange,
  daysCovered,
  ledger,
  refresh,
} = useDashboard()

// Re-fetch dashboard data when a bank enrollment completes.
const teller = useTellerStore()
watch(() => teller.status, (newStatus, oldStatus) => {
  if (oldStatus === 'syncing' && newStatus === 'active') {
    refresh()
  }
})

// User-configurable risk thresholds (Critical / Tight in dollars).
// Defaults match the backend if the user hasn't overridden them.
const auth = useAuthStore()
const criticalThreshold = computed(() => parseMoney(auth.user?.risk_critical_threshold ?? '500'))
const tightThreshold = computed(() => parseMoney(auth.user?.risk_tight_threshold ?? '1000'))

const {
  worstWindow,
  expenseWave,
  dailyExpenseStack,
  masterExpenseOrder,
  masterColorMap,
  billsAnalysis,
  shortfall,
} = useExpenseAnalysis(
  trajectory,
  computed(() => riskAnalysis.value.negativeDate),
  computed(() => riskAnalysis.value.negativeBalance),
)

const nextWeekLabel = computed(() => {
  const start = billsAnalysis.value.nextWeekStart
  if (!start) return ''
  return parseLocalDate(start).toLocaleDateString(getDateLocale(), { month: 'short', day: 'numeric' })
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
