<template>
  <div class="wrap">
    <!-- Date controls -->
    <div class="sim-controls">
      <div class="ctrl-field">
        <span class="ctrl-label">Start Date</span>
        <input type="date" class="ctrl-input" v-model="startDate" @change="updateInfo" />
      </div>
      <div class="ctrl-field">
        <span class="ctrl-label">End Date</span>
        <input type="date" class="ctrl-input" v-model="endDate" @change="updateInfo" />
      </div>
      <button class="sim-btn" @click="runSimulation" :disabled="loading">
        {{ loading ? 'Running...' : 'Run Simulation' }}
      </button>
      <span class="sim-info">{{ dayWindow }} day window</span>
    </div>

    <!-- Loading / error states -->
    <div v-if="loading" class="empty-state">Running simulation...</div>
    <div v-else-if="error" class="empty-state" style="color: var(--danger)">{{ error }}</div>
    <template v-else-if="hasRun && trajectory.length">
      <!-- Hero strip -->
      <div class="hero-strip">
        <div class="hs-card">
          <div class="hs-val" style="color: var(--bright)">{{ fmtInt(currentBalance) }}</div>
          <div class="hs-lbl">Current</div>
        </div>
        <div class="hs-card">
          <div class="hs-val" :style="{ color: afterBalance >= currentBalance ? 'var(--safe)' : 'var(--danger)' }">
            {{ fmtInt(afterBalance) }}
          </div>
          <div class="hs-lbl">After Window</div>
        </div>
        <div class="hs-card">
          <div class="hs-val" style="color: var(--danger)">{{ lowestPoint ? fmtInt(lowestPoint.balance) : '-' }}</div>
          <div v-if="lowestPoint" class="hs-sub">{{ shortDate(lowestPoint.date) }}</div>
          <div class="hs-lbl">Lowest Point</div>
        </div>
        <div class="hs-card">
          <div class="hs-val" :style="{ color: avgGainedPerMonth >= 0 ? 'var(--safe)' : 'var(--danger)' }">
            {{ avgGainedPerMonth >= 0 ? '+' : '-' }}{{ fmtInt(avgGainedPerMonth) }}
          </div>
          <div class="hs-lbl">Avg Gained / Month</div>
        </div>
      </div>

      <!-- Trajectory Chart (reused component) -->
      <TrajectoryChart :data="trajectory" />

      <!-- Monthly Breakdown -->
      <div class="sh">
        <span class="sh-t">Monthly Breakdown</span>
        <span class="sh-m">{{ monthBreaks.length }} months</span>
      </div>
      <div class="month-grid">
        <div v-for="month in monthBreaks" :key="month.label" class="mo-card">
          <div class="mo-header">
            <span class="mo-name">{{ month.label }}</span>
            <span class="mo-net" :class="month.net >= 0 ? 'pos' : 'neg'">
              {{ month.net >= 0 ? '+' : '-' }}{{ fmtInt(month.net) }}
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
              <span class="mo-val">{{ fmtInt(month.startBal) }}</span>
            </div>
            <div class="mo-end">
              <span class="mo-date-label">{{ shortDate(month.endDate) }}</span>
              <span class="mo-val">{{ fmtInt(month.endBal) }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Empty state -->
    <div v-else-if="hasRun" class="empty-state">
      <h3>No Data</h3>
      <p>No projection data returned for the selected window. Check your commitments and balance.</p>
    </div>
    <div v-else class="empty-state">
      <h3>Configure & Run</h3>
      <p>Set your date range above and click "Run Simulation" to project your cash flow trajectory.</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import TrajectoryChart from '@/components/TrajectoryChart.vue'
import { useSimulation } from '@/composables/useSimulation'
import { parseLocalDate } from '@/utils/format'

const {
  startDate,
  endDate,
  hasRun,
  loading,
  error,
  runSimulation,
  trajectory,
  dayWindow,
  currentBalance,
  afterBalance,
  lowestPoint,
  avgGainedPerMonth,
  monthBreaks,
} = useSimulation()

const fmtInt = (n: number) =>
  '$' + Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })

const shortDate = (d: string) =>
  parseLocalDate(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

const maxAbsNet = computed(() => Math.max(...monthBreaks.value.map(m => Math.abs(m.net)), 1))

function barPercent(net: number): number {
  return Math.min((Math.abs(net) / maxAbsNet.value) * 100, 100)
}

function updateInfo() {
  // Reactive dayWindow auto-updates via computed.
}
</script>

<style scoped>
.wrap {
  max-width: 1060px;
  margin: 0 auto;
  padding: 32px 24px 48px;
}

/* Date picker row */
.sim-controls {
  display: flex;
  gap: 14px;
  align-items: flex-end;
  flex-wrap: wrap;
  margin-bottom: 28px;
}

.ctrl-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ctrl-label {
  font-size: 8px;
  font-weight: 700;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.ctrl-input {
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  color: var(--bright);
  font-family: var(--font-sans);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
  min-width: 160px;
}

.ctrl-input:focus {
  border-color: rgba(167, 139, 250, 0.3);
}

.sim-btn {
  padding: 10px 24px;
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid rgba(167, 139, 250, 0.2);
  background: rgba(167, 139, 250, 0.1);
  color: var(--income);
  transition: all 0.15s;
  height: 41px;
}

.sim-btn:hover:not(:disabled) {
  background: rgba(167, 139, 250, 0.2);
}

.sim-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sim-info {
  font-size: 11px;
  color: var(--dim);
  margin-left: auto;
  align-self: center;
  font-family: var(--font-mono);
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
  border-radius: 2px;
  overflow: hidden;
  margin: 8px 0;
}

.mo-bar-fill {
  height: 100%;
  border-radius: 2px;
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

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--dim);
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

@media (max-width: 700px) {
  .hero-strip { gap: 8px; }
  .hs-card { min-width: 100px; padding: 12px; }
  .sim-controls { flex-direction: column; align-items: stretch; }
  .sim-info { margin-left: 0; margin-top: 8px; }
}
</style>
