<template>
  <section class="hero" :class="statusClass">
    <div class="hero-glass" :class="{ danger: statusClass === 'danger' }">
      <div class="hero-days">{{ daysCovered }}</div>
      <div class="hero-label">Day Projection</div>
      <div class="hero-verdict" :class="statusClass">{{ verdict }}</div>
    </div>

    <div class="hero-strip">
      <div class="hs-card">
        <div class="hs-val" :style="{ color: 'var(--bright)' }">{{ fmtShort(currentBalance) }}</div>
        <div class="hs-lbl">Current</div>
      </div>
      <div class="hs-card">
        <div class="hs-val" :style="{ color: endColor }">{{ fmtShort(endBalance) }}</div>
        <div class="hs-lbl">After Window</div>
      </div>
      <div class="hs-card">
        <div class="hs-val" :style="{ color: 'var(--danger)' }">{{ fmtShort(lowestBalance) }}</div>
        <div class="hs-sub">{{ lowestDate }}</div>
        <div class="hs-lbl">Lowest Point</div>
      </div>
      <div class="hs-card">
        <div class="hs-val" :style="{ color: netColor }">{{ netLabel }}</div>
        <div class="hs-lbl">Net Change</div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { formatCurrency, parseLocalDate } from '@/utils/format'

const props = defineProps<{
  currentBalance: number
  endBalance: number
  netChange: number
  lowestBalance: number
  lowestDate: string
  daysCovered: number
}>()

const fmtShort = (n: number) =>
  '$' + Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })

const statusClass = computed(() => {
  if (props.lowestBalance < 0) return 'danger'
  if (props.lowestBalance < 3000) return 'tight'
  return 'safe'
})

const verdict = computed(() => {
  if (statusClass.value === 'danger') return 'Critical'
  if (statusClass.value === 'tight') return 'Tight'
  return 'Comfortable'
})

const endColor = computed(() =>
  props.endBalance >= props.currentBalance ? 'var(--safe)' : 'var(--danger)'
)

const netColor = computed(() =>
  props.netChange >= 0 ? 'var(--safe)' : 'var(--danger)'
)

const netLabel = computed(() => {
  const sign = props.netChange >= 0 ? '+' : '-'
  return `${sign}${fmtShort(props.netChange)}`
})

const lowestDate = computed(() => {
  if (!props.lowestDate) return ''
  return parseLocalDate(props.lowestDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
})
</script>

<style scoped>
.hero {
  padding: 48px 32px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  overflow: hidden;
}

.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.hero.safe::before {
  background: radial-gradient(ellipse 40% 50% at 50% 0%, var(--safe-glow), transparent);
}

.hero.tight::before {
  background: radial-gradient(ellipse 40% 50% at 50% 0%, var(--tight-glow), transparent);
}

.hero.danger::before {
  background: radial-gradient(ellipse 40% 50% at 50% 0%, var(--danger-glow), transparent);
}

.hero-glass {
  position: relative;
  z-index: 1;
  backdrop-filter: blur(16px);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  padding: 28px 40px 24px;
  text-align: center;
  max-width: 380px;
  width: 100%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.hero-glass.danger {
  border-color: rgba(248, 113, 113, 0.15);
  box-shadow: 0 0 0 1px rgba(248, 113, 113, 0.05), 0 0 40px rgba(248, 113, 113, 0.08);
}

.hero-days {
  font-family: var(--font-mono);
  font-size: 80px;
  font-weight: 700;
  line-height: 0.85;
  color: var(--bright);
}

.hero-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.25em;
  margin-top: 8px;
}

.hero-verdict {
  font-size: 18px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: 18px;
}

.hero-verdict.safe { color: var(--safe); }
.hero-verdict.tight { color: var(--tight); }
.hero-verdict.danger { color: var(--danger); }

.hero-strip {
  display: flex;
  gap: 28px;
  margin-top: 24px;
  position: relative;
  z-index: 1;
}

.hs-card {
  backdrop-filter: blur(16px);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px 18px;
  text-align: center;
  min-width: 120px;
  box-shadow: var(--shadow-sm);
}

.hs-val {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
}

.hs-sub {
  font-size: 8px;
  color: var(--muted);
  font-family: var(--font-mono);
  margin-top: 1px;
}

.hs-lbl {
  font-size: 8px;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: 3px;
  font-weight: 700;
}

@media (max-width: 700px) {
  .hero-days { font-size: 56px; }
  .hero-strip { gap: 10px; flex-wrap: wrap; }
  .hs-card { min-width: 80px; padding: 10px 12px; }
}
</style>
