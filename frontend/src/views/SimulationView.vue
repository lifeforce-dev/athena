<template>
  <div class="wrap">
    <!-- ══════════════ SIMULATION RESULTS (above the grid) ══════════════ -->
    <div v-if="loading" class="empty-state">{{ t('sim.running') }}</div>
    <div v-else-if="error" class="empty-state" style="color: var(--danger)">{{ error }}</div>

    <template v-else-if="hasRun && trajectory.length">
      <div class="sim-results">
        <!-- Hero strip -->
        <div class="hero-strip">
          <div class="hs-card">
            <div class="hs-val" style="color: var(--bright)">{{ formatDollars(currentBalance) }}</div>
            <div class="hs-lbl">{{ t('sim.current') }}</div>
          </div>
          <div class="hs-card">
            <div class="hs-val" :style="{ color: afterBalance >= currentBalance ? 'var(--safe)' : 'var(--danger)' }">
              {{ formatDollars(afterBalance) }}
            </div>
            <div class="hs-lbl">{{ t('sim.after_window') }}</div>
          </div>
          <div class="hs-card">
            <div class="hs-val" style="color: var(--danger)">
              {{ lowestPoint ? formatDollars(lowestPoint.balance) : '-' }}
            </div>
            <div v-if="lowestPoint" class="hs-sub">{{ shortDate(lowestPoint.date) }}</div>
            <div class="hs-lbl">{{ t('sim.lowest_point') }}</div>
          </div>
          <div class="hs-card">
            <div class="hs-val" :style="{ color: avgGainedPerMonth >= 0 ? 'var(--safe)' : 'var(--danger)' }">
              {{ avgGainedPerMonth >= 0 ? '+' : '-' }}{{ formatDollars(avgGainedPerMonth) }}
            </div>
            <div class="hs-lbl">{{ t('sim.avg_gained') }}</div>
          </div>
        </div>

        <!-- Trajectory chart -->
        <TrajectoryChart :data="trajectory" />

        <!-- Monthly breakdown -->
        <div class="sh">
          <span class="sh-t">{{ t('sim.monthly_breakdown') }}</span>
          <span class="sh-m">{{ t('sim.months_count', { count: monthBreaks.length }) }}</span>
        </div>
        <div class="month-grid">
          <div v-for="month in monthBreaks" :key="month.label" class="mo-card">
            <div class="mo-header">
              <span class="mo-name">{{ month.label }}</span>
              <span class="mo-net" :class="month.net >= 0 ? 'pos' : 'neg'">
                {{ month.net >= 0 ? '+' : '-' }}{{ formatDollars(month.net) }}
              </span>
            </div>
            <div class="mo-bar">
              <div
                class="mo-bar-fill"
                :style="{
                  width: barPercent(month.net) + '%',
                  background: month.net >= 0 ? 'var(--safe)' : 'var(--danger)',
                }"
              />
            </div>
            <div class="mo-stats">
              <div class="mo-start">
                <span class="mo-date-label">{{ shortDate(month.startDate) }}</span>
                <span class="mo-val">{{ formatDollars(month.startBal) }}</span>
              </div>
              <div class="mo-end">
                <span class="mo-date-label">{{ shortDate(month.endDate) }}</span>
                <span class="mo-val">{{ formatDollars(month.endBal) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else-if="hasRun" class="empty-state">
      <h3>{{ t('sim.no_data_title') }}</h3>
      <p>{{ t('sim.no_data_desc') }}</p>
    </div>

    <!-- ══════════════ TWO-PANEL: Rails left, Sticky Summary right ══════════════ -->
    <div class="scenario-grid" data-tour="sim-grid">
      <!-- LEFT: Commitment rails -->
      <ScenarioCommitments
        :commitments="commitments"
        :overrides="overrides"
        :scenario-income="scenarioIncome"
        :scenario-expenses="scenarioExpenses"
        @toggle="toggleCommitment"
        @amount-change="setAmountOverride"
      />

      <!-- RIGHT: Sticky scenario summary -->
      <div class="summary-panel" data-tour="sim-summary">
        <div class="summary-box">
          <div class="summary-title">{{ t('sim.summary_title') }}</div>
          <div class="summary-body">
            <!-- Date pickers -->
            <div class="date-row">
              <div class="date-field">
                <span class="date-label">{{ t('sim.start_date') }}</span>
                <input type="date" class="date-input" v-model="startDate" />
              </div>
              <div class="date-field">
                <span class="date-label">{{ t('sim.end_date') }}</span>
                <input type="date" class="date-input" v-model="endDate" />
              </div>
            </div>

            <!-- Big net number -->
            <div class="s-big" :class="scenarioNet >= 0 ? '' : 'neg'">
              {{ scenarioNet >= 0 ? '+' : '-' }}{{ formatDollars(scenarioNet) }}
            </div>
            <div class="s-sub">{{ t('sim.net_per_month') }}</div>

            <!-- Breakdown -->
            <div class="s-line">
              <span class="s-line-name">{{ t('sim.income') }}</span>
              <span class="s-line-val" style="color: var(--income)">
                +{{ formatDollars(scenarioIncome) }}
              </span>
            </div>
            <div class="s-line">
              <span class="s-line-name">{{ t('sim.expenses') }}</span>
              <span class="s-line-val" style="color: var(--danger)">
                -{{ formatDollars(scenarioExpenses) }}
              </span>
            </div>

            <hr class="s-divider" />

            <div class="s-line">
              <span class="s-line-name">{{ t('sim.active_items') }}</span>
              <span class="s-line-val" style="color: var(--bright)">
                {{ commitments.length - disabledCount }} / {{ commitments.length }}
              </span>
            </div>
            <div v-if="savingsFromCuts > 0" class="s-line">
              <span class="s-line-name">{{ t('sim.savings_from_cuts') }}</span>
              <span class="s-line-val" style="color: var(--safe)">
                +{{ formatDollars(savingsFromCuts) }}{{ t('commit.per_month') }}
              </span>
            </div>

            <div v-if="hasChanges" class="changes-note">
              <template v-if="disabledCount">{{ t('sim.disabled_count', { count: disabledCount }) }}</template>
              <template v-if="disabledCount && editedCount">, </template>
              <template v-if="editedCount">{{ t('sim.edited_count', { count: editedCount }) }}</template>
              <span class="reset-link" @click="resetOverrides">{{ t('sim.reset') }}</span>
            </div>

            <button class="run-btn" @click="runSimulation" :disabled="loading">
              {{ loading ? t('sim.running_button') : t('sim.run_button') }}
            </button>

            <div class="window-note">{{ t('sim.day_window', { count: dayWindow }) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pre-run placeholder (only if never run and no results) -->
    <div v-if="!hasRun && !loading" class="empty-state pre-run">
      <h3>{{ t('sim.configure_title') }}</h3>
      <p>{{ t('sim.configure_desc') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import TrajectoryChart from '@/components/TrajectoryChart.vue'
import ScenarioCommitments from '@/components/ScenarioCommitments.vue'
import { useScenario } from '@/composables/useScenario'
import { useTour } from '@/composables/useTour'
import { parseLocalDate, formatDollars } from '@/utils/format'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()
useTour()

const {
  commitments,
  overrides,
  toggleCommitment,
  setAmountOverride,
  resetOverrides,
  scenarioIncome,
  scenarioExpenses,
  scenarioNet,
  disabledCount,
  editedCount,
  hasChanges,
  savingsFromCuts,
  startDate,
  endDate,
  dayWindow,
  hasRun,
  loading,
  error,
  runSimulation,
  trajectory,
  currentBalance,
  afterBalance,
  lowestPoint,
  avgGainedPerMonth,
  monthBreaks,
} = useScenario()

const shortDate = (dateStr: string) =>
  parseLocalDate(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

const maxAbsNet = computed(() => Math.max(...monthBreaks.value.map(month => Math.abs(month.net)), 1))

function barPercent(net: number): number {
  return Math.min((Math.abs(net) / maxAbsNet.value) * 100, 100)
}
</script>

<style scoped>
.wrap {
  max-width: 1060px;
  margin: 0 auto;
  padding: 32px 24px 48px;
}

/* ══════════════════════════════════════════
   SIMULATION RESULTS — full-width above grid
   ══════════════════════════════════════════ */

.sim-results {
  margin-bottom: 28px;
}

/* Hero strip */
.hero-strip {
  display: flex;
  gap: 14px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.hs-card {
  backdrop-filter: blur(16px);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  text-align: center;
  flex: 1;
  min-width: 140px;
  box-shadow: var(--shadow-sm);
}

.hs-val {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 700;
}

.hs-sub {
  font-size: 8px;
  color: var(--muted);
  font-family: var(--font-mono);
  margin-top: 2px;
}

.hs-lbl {
  font-size: 8px;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: 4px;
  font-weight: 700;
}

/* Section headers */
.sh {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin: 20px 0 10px;
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

/* Monthly breakdown */
.month-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
  margin-top: 12px;
}

.mo-card {
  backdrop-filter: blur(16px);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
  box-shadow: var(--shadow-sm);
}

.mo-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.mo-name {
  font-size: 11px;
  font-weight: 700;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.mo-net {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
}

.mo-net.pos { color: var(--safe); }
.mo-net.neg { color: var(--danger); }

.mo-bar {
  width: 100%;
  height: 4px;
  background: var(--muted);
  overflow: hidden;
  margin: 8px 0;
}

.mo-bar-fill {
  height: 100%;
  transition: width 0.3s;
}

.mo-stats {
  display: flex;
  justify-content: space-between;
  font-size: 9px;
  color: var(--dim);
  font-family: var(--font-mono);
}

.mo-start,
.mo-end {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.mo-end {
  text-align: right;
}

.mo-date-label {
  font-size: 7px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.mo-val {
  color: var(--text);
  font-weight: 600;
  font-size: 10px;
}

/* ══════════════════════════════════════════
   TWO-PANEL GRID
   ══════════════════════════════════════════ */

.scenario-grid {
  display: grid;
  grid-template-columns: 1fr 290px;
  gap: 24px;
  align-items: start;
}

/* ── Right panel: sticky summary ── */

.summary-panel {
  position: sticky;
  top: 24px;
}

.summary-box {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.summary-title {
  padding: 10px 16px;
  background: var(--raised);
  border-bottom: 1px solid var(--border);
  font-size: 9px;
  font-weight: 700;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.summary-body {
  padding: 18px 16px 16px;
}

/* ── Date pickers ── */

.date-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 18px;
}

.date-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.date-label {
  font-size: 8px;
  font-weight: 700;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.date-input {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--bright);
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 7px 8px;
  outline: none;
  transition: border-color 0.15s;
}

.date-input:focus {
  border-color: rgba(167, 139, 250, 0.3);
}

/* ── Big number ── */

.s-big {
  font-family: var(--font-mono);
  font-size: 28px;
  font-weight: 700;
  color: var(--safe);
  margin-bottom: 2px;
}

.s-big.neg { color: var(--danger); }

.s-sub {
  font-size: 9px;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
  margin-bottom: 18px;
}

/* ── Breakdown lines ── */

.s-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  font-size: 11px;
}

.s-line:last-child { border-bottom: none; }

.s-line-name {
  color: var(--dim);
  font-weight: 500;
}

.s-line-val {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 11px;
}

.s-divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 12px 0;
}

.changes-note {
  font-size: 10px;
  color: var(--tight);
  font-family: var(--font-mono);
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.reset-link {
  color: var(--dim);
  margin-left: 8px;
  cursor: pointer;
  text-decoration: underline;
  font-size: 9px;
  transition: color 0.15s;
}

.reset-link:hover {
  color: var(--text);
}

/* ── Run button ── */

.run-btn {
  width: 100%;
  margin-top: 14px;
  padding: 12px 0;
  border: 1px solid rgba(167, 139, 250, 0.2);
  border-radius: var(--radius-sm);
  background: rgba(167, 139, 250, 0.1);
  color: var(--income);
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}

.run-btn:hover:not(:disabled) {
  background: rgba(167, 139, 250, 0.2);
}

.run-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.window-note {
  font-size: 10px;
  color: var(--dim);
  font-family: var(--font-mono);
  text-align: center;
  margin-top: 8px;
}

/* ══════════════════════════════════════════
   EMPTY / PRE-RUN
   ══════════════════════════════════════════ */

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--dim);
}

.empty-state.pre-run {
  padding: 40px 20px;
}

.empty-state h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}

.empty-state p {
  font-size: 12px;
  max-width: 400px;
  margin: 0 auto;
}

/* ══════════════════════════════════════════
   RESPONSIVE
   ══════════════════════════════════════════ */

@media (max-width: 740px) {
  .scenario-grid {
    grid-template-columns: 1fr;
  }
  .summary-panel {
    position: static;
    order: -1;
  }
  .hero-strip { gap: 8px; }
  .hs-card { min-width: 100px; padding: 12px; }
}
</style>
