<template>
  <nav class="nav">
    <div class="nav-brand">{{ t('login.brand') }}</div>
    <div class="nav-tabs">
      <router-link
        v-for="tab in tabs"
        :key="tab.to"
        :to="tab.to"
        class="nt"
        active-class="active"
      >
        {{ tab.label }}
      </router-link>
    </div>
    <div class="nav-spacer" />
    <div class="nav-currency-wrap" data-tour="currency-toggle">
      <button
        class="nav-currency"
        :class="{ converted: currency.isConverted }"
        :disabled="currency.rateLoading"
        @click="showCurrencyDropdown = !showCurrencyDropdown"
      >
        {{ currencyLabel }}
        <span class="nav-currency-caret">&#9662;</span>
      </button>
      <div v-if="showCurrencyDropdown" class="nav-currency-dropdown">
        <button
          v-for="opt in currencyOptions"
          :key="opt.code"
          class="nav-currency-item"
          :class="{ active: opt.code === currency.displayCurrency }"
          @click="selectCurrency(opt.code)"
        >
          <span class="nci-symbol">{{ opt.symbol }}</span>
          <span class="nci-code">{{ opt.code }}</span>
        </button>
      </div>
    </div>
    <span v-if="auth.user" class="nav-user">{{ auth.user.username }}</span>
    <button v-if="devMode" class="nav-dev-reset" :disabled="resetting" @click="handleDevReset">
      {{ resetting ? 'Resetting...' : 'Reset' }}
    </button>
    <button class="nav-logout" @click="handleLogout">{{ t('nav.logout') }}</button>
  </nav>

  <CurrencyExplainer
    v-if="showExplainer"
    :account-ccy="currency.accountCurrency"
    :display-ccy="currency.displayCurrency"
    @dismiss="onExplainerDismiss"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCurrencyStore } from '@/stores/currency'
import { dismissModal } from '@/api/auth'
import { fetchDevStatus, resetUser } from '@/api/dev'
import { useI18n } from '@/composables/useI18n'
import { getCurrencyConfig, CURRENCIES, CURRENCY_CODES, type CurrencyCode } from '@/config/currencies'
import CurrencyExplainer from '@/components/CurrencyExplainer.vue'

const EXPLAINER_KEY = 'currency-explainer'

const { t } = useI18n()
const auth = useAuthStore()
const currency = useCurrencyStore()
const router = useRouter()
const showExplainer = ref(false)
const showCurrencyDropdown = ref(false)
const devMode = ref(false)
const resetting = ref(false)

const currencyOptions = CURRENCY_CODES.map((code) => ({
  code,
  symbol: CURRENCIES[code].symbol,
}))

onMounted(async () => {
  try {
    const status = await fetchDevStatus()
    devMode.value = status.dev_mode
  } catch {
    // Not critical -- default to hidden.
  }

  document.addEventListener('click', onClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside)
})

function onClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.nav-currency-wrap')) {
    showCurrencyDropdown.value = false
  }
}

const tabs = [
  { to: '/', label: t('nav.dashboard') },
  { to: '/commitments', label: t('nav.commitments') },
  { to: '/simulation', label: t('nav.simulation') },
]

const currencyLabel = computed(() => {
  const cfg = getCurrencyConfig(currency.displayCurrency)
  return `${cfg.symbol} ${currency.displayCurrency}`
})

function hasSeenExplainer(): boolean {
  return (auth.user?.dismissed_modals ?? []).includes(EXPLAINER_KEY)
}

async function selectCurrency(code: CurrencyCode) {
  showCurrencyDropdown.value = false
  await currency.setDisplay(code)

  // Show explainer once on the first selection that switches away from account currency.
  if (currency.isConverted && !hasSeenExplainer()) {
    showExplainer.value = true
  }
}

async function onExplainerDismiss() {
  showExplainer.value = false

  // Persist so it never shows again.
  if (auth.user && !hasSeenExplainer()) {
    try {
      await dismissModal(EXPLAINER_KEY)
      auth.user.dismissed_modals = [...(auth.user.dismissed_modals ?? []), EXPLAINER_KEY]
    } catch {
      // Non-critical, explainer still ran.
    }
  }
}

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}

async function handleDevReset() {
  if (resetting.value) return
  resetting.value = true
  try {
    await resetUser()
    window.location.reload()
  } catch (err) {
    console.error('Dev reset failed:', err)
  } finally {
    resetting.value = false
  }
}
</script>

<style scoped>
.nav {
  display: flex;
  align-items: center;
  backdrop-filter: blur(24px);
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 10;
}

.nav-brand {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 11px;
  color: var(--bright);
  padding: 0 20px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.nav-tabs {
  display: flex;
  margin-left: 8px;
}

.nt {
  padding: 14px 18px;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--dim);
  cursor: pointer;
  transition: color 0.2s;
  display: block;
  text-decoration: none;
}

.nt:hover {
  color: var(--text);
}

.nt.active {
  color: var(--bright);
}

.nt.active::after {
  content: '';
  display: block;
  width: 4px;
  height: 4px;
  margin: 4px auto 0;
  border-radius: 50%;
  background: var(--income);
}

.nav-spacer {
  flex: 1;
}

.nav-currency-wrap {
  position: relative;
}

.nav-currency {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--dim);
  background: none;
  border: 1px solid transparent;
  padding: 6px 12px;
  margin-right: 4px;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}

.nav-currency-caret {
  font-size: 7px;
  margin-left: 2px;
  opacity: 0.5;
}

.nav-currency:hover {
  color: var(--text);
  border-color: var(--border);
}

.nav-currency.converted {
  color: var(--income);
  border-color: color-mix(in srgb, var(--income) 30%, transparent);
}

.nav-currency:disabled {
  opacity: 0.4;
  cursor: wait;
}

.nav-currency-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--panel);
  border: 1px solid var(--border);
  z-index: 20;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px;
  padding: 6px;
  min-width: 160px;
}

.nav-currency-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: none;
  border: 1px solid transparent;
  color: var(--dim);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  transition: color 0.15s, border-color 0.15s;
}

.nav-currency-item:hover {
  color: var(--text);
  border-color: var(--border);
}

.nav-currency-item.active {
  color: var(--income);
  border-color: color-mix(in srgb, var(--income) 30%, transparent);
}

.nci-symbol {
  font-size: 12px;
  width: 16px;
  text-align: center;
}

.nci-code {
  letter-spacing: 0.06em;
}

.nav-user {
  font-size: 11px;
  color: var(--dim);
  padding: 0 8px;
  white-space: nowrap;
}

.nav-logout {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--dim);
  background: none;
  border: none;
  padding: 14px 20px;
  cursor: pointer;
  transition: color 0.2s;
}

.nav-logout:hover {
  color: var(--danger);
}

.nav-dev-reset {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--warning, #e8a735);
  background: none;
  border: 1px solid color-mix(in srgb, var(--warning, #e8a735) 30%, transparent);
  padding: 4px 10px;
  margin-right: 4px;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}

.nav-dev-reset:hover {
  border-color: var(--warning, #e8a735);
}

.nav-dev-reset:disabled {
  opacity: 0.4;
  cursor: wait;
}
</style>
