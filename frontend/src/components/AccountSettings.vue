<template>
  <Teleport to="body">
    <Transition name="settings">
      <div v-if="open" class="settings-overlay" @click.self="$emit('close')">
        <div class="settings-panel">
          <div class="sp-header">
            <span class="sp-title">{{ t('settings.title') }}</span>
            <button class="sp-close" @click="$emit('close')">&times;</button>
          </div>

          <!-- Language -->
          <div class="sp-section">
            <label class="sp-label">{{ t('settings.language') }}</label>
            <p class="sp-desc">{{ t('settings.language_desc') }}</p>
            <div class="sp-select-wrap">
              <select class="sp-select" :value="language.locale" @change="onLanguageChange">
                <option
                  v-for="(label, code) in implementedLocales"
                  :key="code"
                  :value="code"
                >
                  {{ label }}
                </option>
              </select>
              <Transition name="sp-fade">
                <span v-if="langSaved" class="sp-saved">{{ t('settings.saved') }}</span>
              </Transition>
            </div>
            <Transition name="sp-fade">
              <p v-if="showRefreshHint" class="sp-refresh-hint">
                {{ t('settings.language_refresh') }}
                <button class="sp-refresh-btn" @click="reloadPage">&#x21bb;</button>
              </p>
            </Transition>
          </div>

          <!-- Account Currency -->
          <div class="sp-section">
            <label class="sp-label">{{ t('settings.account_currency') }}</label>
            <p class="sp-desc">{{ t('settings.account_currency_desc') }}</p>
            <div class="sp-currency-row">
              <span class="sp-currency-current">
                {{ currentCurrencySymbol }} {{ currency.accountCurrency }}
              </span>
              <button class="sp-change-btn" @click="showCurrencyChange = true">
                {{ t('settings.change_currency') }}
              </button>
            </div>
          </div>

          <!-- Risk Thresholds -->
          <div class="sp-section">
            <label class="sp-label">{{ t('settings.risk_thresholds') }}</label>
            <p class="sp-desc">{{ t('settings.risk_thresholds_desc') }}</p>
            <div class="sp-threshold-grid">
              <div class="sp-threshold-row">
                <span class="sp-threshold-lbl" style="color: var(--danger)">
                  {{ t('settings.critical_below') }}
                </span>
                <div class="sp-threshold-input-wrap">
                  <span class="sp-threshold-prefix">$</span>
                  <input
                    v-model="criticalInput"
                    class="sp-threshold-input"
                    type="number"
                    min="0"
                    step="50"
                    inputmode="numeric"
                  />
                </div>
              </div>
              <div class="sp-threshold-row">
                <span class="sp-threshold-lbl" style="color: var(--tight)">
                  {{ t('settings.tight_below') }}
                </span>
                <div class="sp-threshold-input-wrap">
                  <span class="sp-threshold-prefix">$</span>
                  <input
                    v-model="tightInput"
                    class="sp-threshold-input"
                    type="number"
                    min="0"
                    step="50"
                    inputmode="numeric"
                  />
                </div>
              </div>
            </div>
            <div class="sp-threshold-actions">
              <button
                class="sp-change-btn"
                :disabled="savingThresholds || !thresholdsDirty"
                @click="saveThresholds"
              >
                {{ savingThresholds ? '...' : t('settings.save') }}
              </button>
              <Transition name="sp-fade">
                <span v-if="thresholdsSaved" class="sp-saved">{{ t('settings.saved') }}</span>
              </Transition>
            </div>
            <Transition name="sp-fade">
              <p v-if="thresholdError" class="sp-threshold-error">{{ thresholdError }}</p>
            </Transition>
          </div>

          <!-- Replay Guided Tour -->
          <div class="sp-section">
            <label class="sp-label">{{ t('settings.replay_tour') }}</label>
            <p class="sp-desc">{{ t('settings.replay_tour_desc') }}</p>
            <div class="sp-tour-row">
              <button
                class="sp-change-btn"
                :disabled="resettingTour"
                @click="handleResetTour"
              >
                {{ resettingTour ? '...' : t('settings.replay_tour_btn') }}
              </button>
              <Transition name="sp-fade">
                <span v-if="tourReset" class="sp-saved">{{ t('settings.saved') }}</span>
              </Transition>
            </div>
            <Transition name="sp-fade">
              <p v-if="showTourRefreshHint" class="sp-refresh-hint">
                {{ t('settings.replay_tour_refresh') }}
                <button class="sp-refresh-btn" @click="reloadPage">&#x21bb;</button>
              </p>
            </Transition>
          </div>

          <!-- Currency Change Confirmation -->
          <Transition name="sp-fade">
            <div v-if="showCurrencyChange" class="sp-currency-change">
              <div class="sp-warn-title">{{ t('settings.currency_warning_title') }}</div>
              <p class="sp-warn-text">{{ t('settings.currency_warning') }}</p>
              <div class="sp-currency-grid">
                <button
                  v-for="opt in currencyOptions"
                  :key="opt.code"
                  class="sp-currency-opt"
                  :class="{
                    selected: newCurrency === opt.code,
                    current: opt.code === currency.accountCurrency,
                  }"
                  :disabled="opt.code === currency.accountCurrency || converting"
                  @click="newCurrency = opt.code"
                >
                  <span class="sp-co-symbol">{{ opt.symbol }}</span>
                  <span class="sp-co-code">{{ opt.code }}</span>
                </button>
              </div>
              <div class="sp-warn-actions">
                <button
                  class="sp-cancel"
                  :disabled="converting"
                  @click="showCurrencyChange = false; newCurrency = null"
                >
                  {{ t('settings.currency_cancel') }}
                </button>
                <button
                  class="sp-confirm-danger"
                  :disabled="!newCurrency || converting"
                  @click="confirmCurrencyChange"
                >
                  {{ converting
                    ? t('settings.currency_converting')
                    : t('settings.currency_confirm', { currency: newCurrency ?? '' })
                  }}
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from '@/composables/useI18n'
import { useLanguageStore } from '@/stores/language'
import { useCurrencyStore } from '@/stores/currency'
import { useAuthStore } from '@/stores/auth'
import { changeAccountCurrency } from '@/api/currency'
import { resetTours, setRiskThresholds } from '@/api/auth'
import { resetTourSessionCache } from '@/composables/useTabOnboarding'
import {
  CURRENCIES,
  CURRENCY_CODES,
  IMPLEMENTED_LOCALES,
  getCurrencyConfig,
  type CurrencyCode,
} from '@/config/currencies'

defineProps<{ open: boolean }>()
defineEmits<{ close: [] }>()

const { t } = useI18n()
const language = useLanguageStore()
const currency = useCurrencyStore()
const auth = useAuthStore()

const implementedLocales = IMPLEMENTED_LOCALES

const currentCurrencySymbol = ref(getCurrencyConfig(currency.accountCurrency).symbol)

const langSaved = ref(false)
const showRefreshHint = ref(false)
let langSaveTimeout: ReturnType<typeof setTimeout> | undefined

const resettingTour = ref(false)
const tourReset = ref(false)
const showTourRefreshHint = ref(false)
let tourResetTimeout: ReturnType<typeof setTimeout> | undefined

const showCurrencyChange = ref(false)
const newCurrency = ref<CurrencyCode | null>(null)
const converting = ref(false)

// Risk thresholds — seed from the auth store and track as integer dollars.
const initialCritical = parseFloat(auth.user?.risk_critical_threshold ?? '500')
const initialTight = parseFloat(auth.user?.risk_tight_threshold ?? '1000')
const criticalInput = ref<number>(Math.round(initialCritical))
const tightInput = ref<number>(Math.round(initialTight))
const savingThresholds = ref(false)
const thresholdsSaved = ref(false)
const thresholdError = ref<string | null>(null)
let thresholdSaveTimeout: ReturnType<typeof setTimeout> | undefined

const thresholdsDirty = computed(() => {
  return Number(criticalInput.value) !== Math.round(initialCritical)
    || Number(tightInput.value) !== Math.round(initialTight)
})

// Re-seed if the auth user changes underneath us (e.g. after a fresh /auth/me).
watch(
  () => [auth.user?.risk_critical_threshold, auth.user?.risk_tight_threshold] as const,
  ([crit, tight]) => {
    if (crit != null) criticalInput.value = Math.round(parseFloat(crit))
    if (tight != null) tightInput.value = Math.round(parseFloat(tight))
  },
)

const currencyOptions = CURRENCY_CODES.map((code) => ({
  code,
  symbol: CURRENCIES[code].symbol,
}))

function reloadPage() {
  location.reload()
}

async function handleResetTour() {
  if (resettingTour.value) return
  resettingTour.value = true
  try {
    await resetTours()
    resetTourSessionCache()
    if (auth.user) {
      auth.user.completed_tours = []
    }
    tourReset.value = true
    showTourRefreshHint.value = true
    clearTimeout(tourResetTimeout)
    tourResetTimeout = setTimeout(() => { tourReset.value = false }, 2000)
  } catch (err) {
    console.error('Tour reset failed:', err)
  } finally {
    resettingTour.value = false
  }
}

async function onLanguageChange(event: Event) {
  const select = event.target as HTMLSelectElement
  const newLocale = select.value
  await language.changeLocale(newLocale)

  // Update auth store user object to keep in sync.
  if (auth.user) {
    auth.user.account_language = newLocale
  }

  // Flash "Saved" indicator.
  langSaved.value = true
  showRefreshHint.value = true
  clearTimeout(langSaveTimeout)
  langSaveTimeout = setTimeout(() => { langSaved.value = false }, 2000)
}

async function saveThresholds() {
  if (savingThresholds.value) return

  const critical = Number(criticalInput.value)
  const tight = Number(tightInput.value)

  if (!Number.isFinite(critical) || !Number.isFinite(tight) || critical < 0 || tight < 0) {
    thresholdError.value = t('settings.threshold_error_negative')
    return
  }
  if (critical >= tight) {
    thresholdError.value = t('settings.threshold_error_order')
    return
  }

  thresholdError.value = null
  savingThresholds.value = true

  try {
    await setRiskThresholds(critical, tight)
    if (auth.user) {
      auth.user.risk_critical_threshold = critical.toFixed(2)
      auth.user.risk_tight_threshold = tight.toFixed(2)
    }
    thresholdsSaved.value = true
    clearTimeout(thresholdSaveTimeout)
    thresholdSaveTimeout = setTimeout(() => { thresholdsSaved.value = false }, 2000)
  } catch (err) {
    console.error('Threshold save failed:', err)
    thresholdError.value = t('settings.threshold_error_generic')
  } finally {
    savingThresholds.value = false
  }
}

async function confirmCurrencyChange() {
  if (!newCurrency.value || converting.value) return
  converting.value = true

  try {
    const result = await changeAccountCurrency(newCurrency.value)

    // Update stores with the new currency.
    currency.accountCurrency = result.account_currency as CurrencyCode
    currency.displayCurrency = result.account_currency as CurrencyCode
    currentCurrencySymbol.value = getCurrencyConfig(result.account_currency).symbol

    // Update language to the new currency's default.
    const newLang = CURRENCIES[result.account_currency as CurrencyCode]?.defaultLang ?? 'en_US'
    language.initFromUser(newLang)

    // Sync auth store.
    if (auth.user) {
      auth.user.account_currency = result.account_currency
      auth.user.display_currency = result.account_currency
      auth.user.account_language = newLang
    }

    showCurrencyChange.value = false
    newCurrency.value = null

    // Reload to pick up converted amounts everywhere.
    window.location.reload()
  } catch (err) {
    console.error('Currency change failed:', err)
  } finally {
    converting.value = false
  }
}
</script>

<style scoped>
.settings-overlay {
  position: fixed;
  inset: 0;
  z-index: 9000;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: flex-end;
}

.settings-panel {
  width: 380px;
  max-width: 90vw;
  height: 100%;
  background: var(--panel);
  border-left: 1px solid var(--border);
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.sp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sp-title {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--bright);
}

.sp-close {
  background: none;
  border: none;
  color: var(--dim);
  font-size: 20px;
  cursor: pointer;
  padding: 4px 8px;
  transition: color 0.15s;
}

.sp-close:hover {
  color: var(--text);
}

.sp-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sp-label {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text);
}

.sp-desc {
  font-size: 11px;
  color: var(--dim);
  margin: 0;
  line-height: 1.5;
}

.sp-select-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}

.sp-select {
  flex: 1;
  font-family: var(--font-mono);
  font-size: 12px;
  background: var(--bg);
  color: var(--text);
  border: 1px solid var(--border);
  padding: 8px 12px;
  cursor: pointer;
  appearance: auto;
}

.sp-select:focus {
  outline: none;
  border-color: var(--income);
}

.sp-saved {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--safe);
}

.sp-refresh-hint {
  margin-top: 8px;
  font-size: 11px;
  color: var(--dim);
  display: flex;
  align-items: center;
  gap: 8px;
}

.sp-refresh-btn {
  background: var(--raised);
  border: 1px solid var(--border);
  color: var(--bright);
  font-size: 14px;
  padding: 2px 8px;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background 0.15s;
}

.sp-refresh-btn:hover {
  background: var(--panel);
  border-color: var(--income);
}

.sp-tour-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
}

.sp-currency-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.sp-currency-current {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  color: var(--bright);
}

.sp-change-btn {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--dim);
  background: none;
  border: 1px solid var(--border);
  padding: 6px 14px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}

.sp-change-btn:hover {
  color: var(--text);
  border-color: var(--text);
}

/* Risk thresholds */

.sp-threshold-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
}

.sp-threshold-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sp-threshold-lbl {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.sp-threshold-input-wrap {
  display: flex;
  align-items: center;
  background: var(--bg);
  border: 1px solid var(--border);
  padding: 0 8px;
  width: 120px;
}

.sp-threshold-input-wrap:focus-within {
  border-color: var(--income);
}

.sp-threshold-prefix {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--dim);
  margin-right: 4px;
}

.sp-threshold-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 8px 0;
  width: 100%;
  -moz-appearance: textfield;
}

.sp-threshold-input::-webkit-outer-spin-button,
.sp-threshold-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.sp-threshold-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}

.sp-threshold-error {
  margin: 8px 0 0;
  font-size: 11px;
  color: var(--danger);
  line-height: 1.5;
}

/* Currency change section */

.sp-currency-change {
  background: color-mix(in srgb, var(--danger) 5%, var(--bg));
  border: 1px solid color-mix(in srgb, var(--danger) 30%, transparent);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sp-warn-title {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--danger);
}

.sp-warn-text {
  font-size: 11px;
  color: var(--text);
  line-height: 1.6;
  margin: 0;
}

.sp-currency-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(70px, 1fr));
  gap: 4px;
}

.sp-currency-opt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 4px;
  background: none;
  border: 1px solid var(--border);
  color: var(--dim);
  cursor: pointer;
  font-family: var(--font-mono);
  transition: color 0.15s, border-color 0.15s;
}

.sp-currency-opt:hover:not(:disabled) {
  color: var(--text);
  border-color: var(--text);
}

.sp-currency-opt.selected {
  color: var(--danger);
  border-color: var(--danger);
}

.sp-currency-opt.current {
  opacity: 0.3;
  cursor: default;
}

.sp-co-symbol {
  font-size: 14px;
}

.sp-co-code {
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.sp-warn-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.sp-cancel {
  flex: 1;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--dim);
  background: none;
  border: 1px solid var(--border);
  padding: 10px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}

.sp-cancel:hover {
  color: var(--text);
  border-color: var(--text);
}

.sp-confirm-danger {
  flex: 1;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--bg);
  background: var(--danger);
  border: 1px solid var(--danger);
  padding: 10px;
  cursor: pointer;
  transition: opacity 0.15s;
}

.sp-confirm-danger:hover {
  opacity: 0.85;
}

.sp-confirm-danger:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.sp-cancel:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Transitions */

.settings-enter-active,
.settings-leave-active {
  transition: opacity 0.2s ease;
}

.settings-enter-active .settings-panel,
.settings-leave-active .settings-panel {
  transition: transform 0.2s ease;
}

.settings-enter-from,
.settings-leave-to {
  opacity: 0;
}

.settings-enter-from .settings-panel {
  transform: translateX(100%);
}

.settings-leave-to .settings-panel {
  transform: translateX(100%);
}

.sp-fade-enter-active,
.sp-fade-leave-active {
  transition: opacity 0.2s ease;
}

.sp-fade-enter-from,
.sp-fade-leave-to {
  opacity: 0;
}
</style>
