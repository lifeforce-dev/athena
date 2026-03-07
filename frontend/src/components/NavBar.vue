<template>
  <nav class="nav" :class="{ 'nav-between': fteBetweenTours }">
    <div class="nav-brand">{{ t('login.brand') }}</div>
    <div class="nav-tabs">
      <button v-if="fteActive" class="nt-skip" @click="handleSkipTour">
        {{ t('fte.skip_tour') }}
      </button>
      <router-link
        v-for="tab in tabs"
        :key="tab.to"
        :to="isTabUnlocked(tab.name) ? tab.to : ''"
        class="nt"
        :class="{
          active: isCurrentRoute(tab.to),
          'nt-disabled': !isTabUnlocked(tab.name),
          'nt-glow': isTabGlowing(tab.name),
        }"
        @click.prevent="handleTabClick(tab, $event)"
      >
        {{ tab.label }}
      </router-link>
    </div>
    <div class="nav-spacer" />
    <div class="nav-bank-wrap">
      <button
        class="nav-bank"
        :class="{
          connected: teller.isConnected,
          syncing: teller.isSyncing,
          error: teller.hasError,
        }"
        :disabled="teller.loading"
        @click="handleBankClick"
      >
        <span v-if="teller.isConnected || teller.hasError" class="nav-bank-dot" />
        <template v-if="teller.isSyncing || teller.loading">Syncing...</template>
        <template v-else-if="teller.isConnected">{{ teller.institutionName }}</template>
        <template v-else-if="teller.hasError">Connection Error</template>
        <template v-else>Connect Bank</template>
      </button>
      <div v-if="showBankDropdown" class="nav-bank-dropdown">
        <button class="nav-bank-item" @click="handleReconnect">Reconnect</button>
        <button class="nav-bank-item nav-bank-disconnect" @click="handleDisconnect">Disconnect</button>
      </div>
    </div>
    <TellerConnect ref="tellerConnectRef" @connected="onBankConnected" @cancelled="onBankCancelled" />
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
    <button class="nav-settings" @click="showSettings = true" :title="t('settings.title')">
      &#9881;
    </button>
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

  <AccountSettings :open="showSettings" @close="showSettings = false" />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCurrencyStore } from '@/stores/currency'
import { dismissModal, markTourComplete } from '@/api/auth'
import { fetchDevStatus, resetUser } from '@/api/dev'
import { useI18n } from '@/composables/useI18n'
import { getCurrencyConfig, CURRENCIES, CURRENCY_CODES, type CurrencyCode } from '@/config/currencies'
import CurrencyExplainer from '@/components/CurrencyExplainer.vue'
import AccountSettings from '@/components/AccountSettings.vue'
import TellerConnect from '@/components/TellerConnect.vue'
import { useTellerStore } from '@/stores/teller'
import {
  fteActive,
  fteStarted,
  FTE_STEPS,
  isTabUnlocked,
  isTabGlowing,
  fteBetweenTours,
  endFte,
} from '@/stores/fte'
import { demoTourActive } from '@/stores/demoTour'
import { activeDriver, resetTourSessionCache } from '@/composables/useTabOnboarding'

const EXPLAINER_KEY = 'currency-explainer'

const { t } = useI18n()
const auth = useAuthStore()
const currency = useCurrencyStore()
const teller = useTellerStore()
const router = useRouter()
const route = useRoute()
const showExplainer = ref(false)
const showCurrencyDropdown = ref(false)
const showBankDropdown = ref(false)
const tellerConnectRef = ref<InstanceType<typeof TellerConnect> | null>(null)
const devMode = ref(false)
const resetting = ref(false)
const showSettings = ref(false)

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

  // Fetch Teller connection status if authenticated.
  if (auth.isAuthenticated) {
    teller.fetchStatus()
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
  if (!target.closest('.nav-bank-wrap')) {
    showBankDropdown.value = false
  }
}

const tabs = [
  { to: '/', name: 'dashboard', label: t('nav.dashboard') },
  { to: '/commitments', name: 'commitments', label: t('nav.commitments') },
  { to: '/simulation', name: 'simulation', label: t('nav.simulation') },
]

function isCurrentRoute(path: string): boolean {
  return route.path === path
}

function handleTabClick(tab: { to: string; name: string }, event: MouseEvent) {
  if (!isTabUnlocked(tab.name)) {
    event.preventDefault()
    return
  }

  // During FTE, clicking the first glowing tab marks FTE as started.
  if (fteActive.value && !fteStarted.value) {
    fteStarted.value = true
  }
}

async function handleSkipTour() {
  // Destroy active driver.js tour if running.
  if (activeDriver) {
    activeDriver.destroy()
  }

  // Persist all remaining tours as completed so FTE never re-triggers.
  for (const step of FTE_STEPS) {
    const completed = auth.user?.completed_tours ?? []
    if (!completed.includes(step)) {
      try {
        await markTourComplete(step)
        if (auth.user) {
          auth.user.completed_tours = [...(auth.user.completed_tours ?? []), step]
        }
      } catch {
        // Non-critical.
      }
    }
  }

  endFte()
  demoTourActive.value = false
  window.location.replace('/')
}

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
    if (activeDriver) activeDriver.destroy()
    endFte()
    demoTourActive.value = false
    resetTourSessionCache()
    await resetUser()

    // Mirror server reset on client to avoid stale-data race on slow DBs.
    if (auth.user) {
      auth.user.completed_tours = []
      auth.user.dismissed_modals = []
      auth.user.account_currency = null
      auth.user.display_currency = null
      auth.user.account_language = null
    }
    currency.$reset()
    router.replace('/')
  } catch (err) {
    console.error('Dev reset failed:', err)
  } finally {
    resetting.value = false
  }
}

// -- Bank connection -------------------------------------------------------

function handleBankClick() {
  if (teller.isConnected || teller.hasError) {
    showBankDropdown.value = !showBankDropdown.value
  } else {
    tellerConnectRef.value?.open()
  }
}

function handleReconnect() {
  showBankDropdown.value = false
  tellerConnectRef.value?.open()
}

async function handleDisconnect() {
  showBankDropdown.value = false
  await teller.disconnect()
}

function onBankConnected() {
  teller.fetchStatus()
}

function onBankCancelled() {
  // No action needed — widget closed without completing.
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

/* Between-tours: dim the entire nav, glowing tab + skip pop above. */
.nav-between::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  z-index: 1;
  pointer-events: none;
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

.nt-disabled {
  opacity: 0.25;
  pointer-events: none;
  cursor: default;
}

.nt-glow {
  color: var(--safe) !important;
  animation: nte-pulse 2s ease-in-out infinite;
  position: relative;
  z-index: 2;
}

@keyframes nte-pulse {
  0%, 100% { text-shadow: 0 0 4px transparent; }
  50% { text-shadow: 0 0 12px var(--safe); }
}

.nt-skip {
  color: var(--muted);
  background: none;
  border: 1px solid var(--muted);
  border-radius: 4px;
  padding: 4px 12px;
  font-size: 8px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  cursor: pointer;
  margin-right: 8px;
  align-self: center;
  transition: color 0.2s, border-color 0.2s;
  position: relative;
  z-index: 2;
}

.nt-skip:hover {
  color: var(--text);
  border-color: var(--text);
}

.nav-spacer {
  flex: 1;
}

/* -- Bank button & dropdown --------------------------------------------- */

.nav-bank-wrap {
  position: relative;
}

.nav-bank {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--dim);
  background: none;
  border: 1px solid transparent;
  padding: 6px 12px;
  margin-right: 4px;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.nav-bank:hover {
  color: var(--text);
  border-color: var(--border);
}

.nav-bank.connected {
  color: var(--safe);
  border-color: color-mix(in srgb, var(--safe) 30%, transparent);
}

.nav-bank.syncing {
  color: var(--dim);
  opacity: 0.6;
  cursor: wait;
}

.nav-bank.error {
  color: var(--danger);
  border-color: color-mix(in srgb, var(--danger) 30%, transparent);
}

.nav-bank-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--safe);
  flex-shrink: 0;
}

.nav-bank.error .nav-bank-dot {
  background: var(--danger);
}

.nav-bank-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--panel);
  border: 1px solid var(--border);
  z-index: 20;
  padding: 4px;
  min-width: 140px;
}

.nav-bank-item {
  display: block;
  width: 100%;
  padding: 6px 10px;
  background: none;
  border: 1px solid transparent;
  color: var(--dim);
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-align: left;
  transition: color 0.15s, border-color 0.15s;
}

.nav-bank-item:hover {
  color: var(--text);
  border-color: var(--border);
}

.nav-bank-disconnect:hover {
  color: var(--danger);
  border-color: color-mix(in srgb, var(--danger) 30%, transparent);
}

/* -- Currency toggle ---------------------------------------------------- */

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

.nav-settings {
  font-size: 14px;
  color: var(--dim);
  background: none;
  border: none;
  padding: 6px 8px;
  cursor: pointer;
  transition: color 0.2s;
  line-height: 1;
}

.nav-settings:hover {
  color: var(--text);
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
