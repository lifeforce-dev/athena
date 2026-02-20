import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { setAccountCurrency, setDisplayCurrency as apiSetDisplayCurrency, fetchExchangeRate } from '@/api/currency'
import { setCurrencyDisplay } from '@/utils/format'

export type CurrencyCode = 'USD' | 'KRW'

export const useCurrencyStore = defineStore('currency', () => {
  /** The user's real-world currency (what's stored in the DB). */
  const accountCurrency = ref<CurrencyCode>('USD')

  /** The currency currently displayed in the UI and used for input. */
  const displayCurrency = ref<CurrencyCode>('USD')

  /** Whether the user has set account_currency on the server. */
  const accountCurrencySet = ref(false)

  /** Cached exchange rate: 1 USD = N KRW. */
  const krwRate = ref<number | null>(null)

  /** True while we're fetching the exchange rate. */
  const rateLoading = ref(false)

  const isConverted = computed(() => displayCurrency.value !== accountCurrency.value)

  // Push display state into the format layer whenever it changes.
  // The rate must convert account currency → display currency so that
  // DB values (stored in account currency) render correctly.
  watch([accountCurrency, displayCurrency, krwRate], () => {
    const acct = accountCurrency.value
    const disp = displayCurrency.value

    let rate = 1
    if (acct !== disp && krwRate.value != null) {
      if (acct === 'USD' && disp === 'KRW') {
        rate = krwRate.value          // USD stored, display KRW: multiply by rate.
      } else if (acct === 'KRW' && disp === 'USD') {
        rate = 1 / krwRate.value      // KRW stored, display USD: divide by rate.
      }
    }
    setCurrencyDisplay({ code: disp, rate })
  }, { immediate: true })

  /**
   * Initialize from the /me response. If account_currency is null,
   * the prompt should be shown.
   */
  function initFromUser(acctCurrency: string | null, displayCurrencyFromServer?: string | null) {
    if (acctCurrency) {
      accountCurrencySet.value = true
      accountCurrency.value = acctCurrency as CurrencyCode
      displayCurrency.value = (displayCurrencyFromServer ?? acctCurrency) as CurrencyCode
    } else {
      accountCurrencySet.value = false
      accountCurrency.value = 'USD'
      displayCurrency.value = 'USD'
    }
  }

  /** Persist the user's currency choice to the server. */
  async function saveAccountCurrency(code: CurrencyCode) {
    await setAccountCurrency(code)
    accountCurrencySet.value = true
    accountCurrency.value = code
    displayCurrency.value = code

    // Keep the auth store's user object in sync.
    const { useAuthStore } = await import('@/stores/auth')
    const auth = useAuthStore()
    if (auth.user) {
      auth.user.account_currency = code
      auth.user.display_currency = code
    }

    // Pre-fetch the exchange rate if they chose KRW.
    if (code === 'KRW' && krwRate.value === null) {
      await loadRate()
    }
  }

  /** Toggle between USD and KRW for display. Persisted to backend. */
  async function toggleDisplay() {
    const newCurrency: CurrencyCode = displayCurrency.value === 'USD' ? 'KRW' : 'USD'

    if (krwRate.value === null) {
      try {
        await loadRate()
      } catch {
        console.error('Failed to fetch exchange rate')
        return
      }
    }

    displayCurrency.value = newCurrency
    await apiSetDisplayCurrency(newCurrency)
  }

  /** Fetch the exchange rate from the backend. */
  async function loadRate() {
    if (rateLoading.value) return
    rateLoading.value = true
    try {
      const resp = await fetchExchangeRate('KRW')
      krwRate.value = resp.rate
    } finally {
      rateLoading.value = false
    }
  }

  /**
   * Convert an account-currency amount to the current display currency.
   * Returns the original value if currencies match or rate is unavailable.
   */
  function convert(amount: number): number {
    if (accountCurrency.value === displayCurrency.value || krwRate.value === null) {
      return amount
    }
    if (accountCurrency.value === 'USD' && displayCurrency.value === 'KRW') {
      return amount * krwRate.value
    }
    if (accountCurrency.value === 'KRW' && displayCurrency.value === 'USD') {
      return amount / krwRate.value
    }
    return amount
  }

  /** Reset on logout. */
  function $reset() {
    accountCurrency.value = 'USD'
    displayCurrency.value = 'USD'
    accountCurrencySet.value = false
    krwRate.value = null
    rateLoading.value = false
  }

  return {
    accountCurrency,
    displayCurrency,
    accountCurrencySet,
    krwRate,
    rateLoading,
    isConverted,
    initFromUser,
    saveAccountCurrency,
    toggleDisplay,
    loadRate,
    convert,
    $reset,
  }
})
