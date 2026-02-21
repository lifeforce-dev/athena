<template>
  <Teleport to="body">
    <Transition name="explainer-fade">
      <div v-if="visible" class="explainer-overlay" @click.self="dismiss">
        <div class="explainer-modal">
          <div class="explainer-header">
            <span class="explainer-icon">&#8644;</span>
            <h2 class="explainer-title">{{ t('explainer.title') }}</h2>
          </div>

          <p class="explainer-desc">
            {{ t('explainer.body', { accountCurrency: accountLabel, displayCurrency: displayLabel }) }}
          </p>

          <!-- Animated round-trip graphic -->
          <div class="roundtrip" :class="{ animate: animating }">
            <!-- Step 1: user enters display amount -->
            <div class="rt-step rt-input">
              <span class="rt-label">{{ t('explainer.you_enter') }}</span>
              <span class="rt-value rt-display-val">{{ displaySymbol }}{{ formatNum(displayAmount) }}</span>
            </div>

            <!-- Arrow 1 -->
            <div class="rt-arrow rt-arrow-down">
              <div class="rt-arrow-track">
                <div class="rt-arrow-fill rt-fill-1" />
              </div>
              <span class="rt-arrow-label">{{ t('explainer.stored_as') }}</span>
            </div>

            <!-- Step 2: stored in account currency -->
            <div class="rt-step rt-stored">
              <span class="rt-label">{{ t('explainer.saved') }}</span>
              <span class="rt-value rt-account-val">{{ accountSymbol }}{{ formatNum(accountAmount) }}</span>
            </div>

            <!-- Arrow 2 -->
            <div class="rt-arrow rt-arrow-down">
              <div class="rt-arrow-track">
                <div class="rt-arrow-fill rt-fill-2" />
              </div>
              <span class="rt-arrow-label">{{ t('explainer.displayed_as') }}</span>
            </div>

            <!-- Step 3: converted back for display -->
            <div class="rt-step rt-result">
              <span class="rt-label">{{ t('explainer.you_see') }}</span>
              <span class="rt-value rt-display-val">{{ displaySymbol }}{{ formatNum(resultAmount) }}</span>
              <span v-if="delta !== 0" class="rt-delta">
                {{ t('explainer.difference', { delta: (delta > 0 ? '+' : '') + formatNum(delta) }) }}
              </span>
            </div>
          </div>

          <button class="explainer-dismiss" @click="dismiss">{{ t('explainer.dismiss') }}</button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCurrencyStore } from '@/stores/currency'
import { useI18n } from '@/composables/useI18n'
import { getCurrencyConfig } from '@/config/currencies'

const props = defineProps<{ accountCcy: string; displayCcy: string }>()
const emit = defineEmits<{ dismiss: [] }>()

const { t } = useI18n()
const currency = useCurrencyStore()
const visible = ref(false)
const animating = ref(false)

const acctCfg = computed(() => getCurrencyConfig(props.accountCcy))
const dispCfg = computed(() => getCurrencyConfig(props.displayCcy))

const accountLabel = computed(() => `${props.accountCcy} (${acctCfg.value.symbol})`)
const displayLabel = computed(() => `${props.displayCcy} (${dispCfg.value.symbol})`)
const accountSymbol = computed(() => acctCfg.value.symbol)
const displaySymbol = computed(() => dispCfg.value.symbol)

/** Get the live rate from the store (account -> display). */
const liveRate = computed(() => {
  const key = `${props.accountCcy}:${props.displayCcy}`
  return currency.rates.get(key) ?? 1
})

// Example amounts: use 100000 for zero-decimal currencies, 100 otherwise.
const displayAmount = computed(() => dispCfg.value.decimals === 0 ? 100000 : 100)
const accountAmount = computed(() => {
  // Display amount -> account currency (divide by live rate).
  const raw = displayAmount.value / liveRate.value

  if (acctCfg.value.decimals === 0) {
    return Math.round(raw)
  }

  return Math.round(raw * 100) / 100
})
const resultAmount = computed(() => {
  // Account amount -> back to display currency (multiply by live rate).
  const raw = accountAmount.value * liveRate.value

  if (dispCfg.value.decimals === 0) {
    return Math.round(raw)
  }

  return Math.round(raw * 100) / 100
})
const delta = computed(() => resultAmount.value - displayAmount.value)

function formatNum(n: number): string {
  return n.toLocaleString('en-US', { maximumFractionDigits: 2 })
}

function dismiss() {
  visible.value = false
  setTimeout(() => emit('dismiss'), 300)
}

onMounted(() => {
  // Stagger entrance so the CSS transitions fire.
  requestAnimationFrame(() => {
    visible.value = true
    setTimeout(() => { animating.value = true }, 400)
  })
})
</script>

<style scoped>
/* ── Overlay + Modal ──────────────────────────────── */
.explainer-overlay {
  position: fixed;
  inset: 0;
  z-index: 9998;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(8px);
}

.explainer-modal {
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 28px 32px 24px;
  max-width: 360px;
  width: 100%;
}

/* ── Transition ───────────────────────────────────── */
.explainer-fade-enter-active,
.explainer-fade-leave-active {
  transition: opacity 0.3s ease;
}
.explainer-fade-enter-active .explainer-modal,
.explainer-fade-leave-active .explainer-modal {
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.explainer-fade-enter-from,
.explainer-fade-leave-to {
  opacity: 0;
}
.explainer-fade-enter-from .explainer-modal {
  transform: translateY(12px);
  opacity: 0;
}
.explainer-fade-leave-to .explainer-modal {
  transform: translateY(-8px);
  opacity: 0;
}

/* ── Header ───────────────────────────────────────── */
.explainer-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.explainer-icon {
  font-size: 18px;
  color: var(--income);
}

.explainer-title {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  color: var(--bright);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin: 0;
}

/* ── Description ──────────────────────────────────── */
.explainer-desc {
  font-size: 12px;
  color: var(--dim);
  line-height: 1.6;
  margin: 0 0 22px;
}

.hl-account {
  color: var(--bright);
  font-weight: 600;
}

.hl-display {
  color: var(--income);
  font-weight: 600;
}

/* ── Round-trip Graphic ───────────────────────────── */
.roundtrip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  margin-bottom: 24px;
}

/* Steps */
.rt-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 10px 20px;
  border: 1px solid var(--border);
  width: 100%;
  text-align: center;
  opacity: 0;
  transform: scale(0.95);
  transition: opacity 0.4s ease, transform 0.4s ease, border-color 0.4s ease;
}

.roundtrip.animate .rt-input {
  opacity: 1;
  transform: scale(1);
  transition-delay: 0s;
}

.roundtrip.animate .rt-stored {
  opacity: 1;
  transform: scale(1);
  transition-delay: 0.7s;
}

.roundtrip.animate .rt-result {
  opacity: 1;
  transform: scale(1);
  transition-delay: 1.4s;
}

.roundtrip.animate .rt-result {
  border-color: color-mix(in srgb, var(--tight) 40%, transparent);
}

.rt-label {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--dim);
}

.rt-value {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.rt-display-val {
  color: var(--income);
}

.rt-account-val {
  color: var(--bright);
}

.rt-delta {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--tight);
  margin-top: 2px;
  opacity: 0;
  transition: opacity 0.4s ease;
  transition-delay: 1.8s;
}

.roundtrip.animate .rt-delta {
  opacity: 1;
}

/* Arrows */
.rt-arrow {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  padding: 4px 0;
}

.rt-arrow-track {
  width: 2px;
  height: 28px;
  background: var(--muted);
  position: relative;
  overflow: hidden;
}

.rt-arrow-fill {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 0%;
  background: var(--income);
  transition: height 0.5s ease;
}

.roundtrip.animate .rt-fill-1 {
  height: 100%;
  transition-delay: 0.3s;
}

.roundtrip.animate .rt-fill-2 {
  height: 100%;
  transition-delay: 1.0s;
}

.rt-arrow-label {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--dim);
  margin-top: 2px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.roundtrip.animate .rt-arrow:first-of-type .rt-arrow-label {
  opacity: 1;
  transition-delay: 0.5s;
}

.roundtrip.animate .rt-arrow:last-of-type .rt-arrow-label {
  opacity: 1;
  transition-delay: 1.2s;
}

/* ── Dismiss Button ───────────────────────────────── */
.explainer-dismiss {
  width: 100%;
  padding: 10px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--bright);
  background: transparent;
  border: 1px solid var(--border);
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}

.explainer-dismiss:hover {
  border-color: var(--income);
  color: var(--income);
}
</style>
