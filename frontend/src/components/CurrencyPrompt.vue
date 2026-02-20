<template>
  <Teleport to="body">
    <div class="currency-overlay">
      <div class="currency-modal">
        <h2 class="cm-title">Set Your Currency</h2>
        <p class="cm-desc">
          Choose your account currency. All amounts will be stored and displayed in this currency.
        </p>

        <div class="cm-options">
          <button
            v-for="opt in options"
            :key="opt.code"
            class="cm-opt"
            :class="{ selected: selected === opt.code }"
            @click="selected = opt.code"
          >
            <span class="cm-opt-symbol">{{ opt.symbol }}</span>
            <span class="cm-opt-label">{{ opt.label }}</span>
          </button>
        </div>

        <button class="cm-confirm" :disabled="!selected || saving" @click="confirm">
          {{ saving ? 'Saving...' : 'Continue' }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useCurrencyStore, type CurrencyCode } from '@/stores/currency'

const currency = useCurrencyStore()
const emit = defineEmits<{ done: [] }>()

const selected = ref<CurrencyCode | null>(null)
const saving = ref(false)

const options = [
  { code: 'USD' as CurrencyCode, symbol: '$', label: 'US Dollar (USD)' },
  { code: 'KRW' as CurrencyCode, symbol: '\u20A9', label: 'Korean Won (KRW)' },
]

async function confirm() {
  if (!selected.value || saving.value) return
  saving.value = true
  try {
    await currency.saveAccountCurrency(selected.value)
    emit('done')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.currency-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
}

.currency-modal {
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 32px 36px;
  max-width: 380px;
  width: 100%;
  text-align: center;
}

.cm-title {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  color: var(--bright);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin: 0 0 12px;
}

.cm-desc {
  font-size: 12px;
  color: var(--dim);
  line-height: 1.5;
  margin: 0 0 24px;
}

.cm-options {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.cm-opt {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px 12px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--dim);
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}

.cm-opt:hover {
  border-color: var(--text);
  color: var(--text);
}

.cm-opt.selected {
  border-color: var(--income);
  color: var(--bright);
}

.cm-opt-symbol {
  font-size: 22px;
  font-weight: 700;
}

.cm-opt-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.cm-confirm {
  width: 100%;
  padding: 10px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--bg);
  background: var(--income);
  border: none;
  cursor: pointer;
  transition: opacity 0.2s;
}

.cm-confirm:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.cm-confirm:not(:disabled):hover {
  opacity: 0.85;
}
</style>
