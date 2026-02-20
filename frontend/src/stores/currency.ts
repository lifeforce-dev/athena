import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { setAccountCurrency, fetchExchangeRate } from '@/api/currency'
import { setCurrencyDisplay } from '@/utils/format'

export type CurrencyCode = 'USD' | 'KRW'

export const useCurrencyStore = defineStore('currency', () => {
  /** The currency currently displayed in the UI (session-only, not persisted). */
  const displayCurrency = ref<CurrencyCode>('USD')

  /** Whether the user has set account_currency on the server. */
  const accountCurrencySet = ref(false)

  /** Cached exchange rate: 1 USD = N KRW. */
  const krwRate = ref<number | null>(null)

  /** True while we're fetching the exchange rate. */
  const rateLoading = ref(false)

  const isConverted = computed(() => displayCurrency.value !== 'USD')

  // Push display state into the format layer whenever it changes.
  watch([displayCurrency, krwRate], () => {
    const rate = displayCurrency.value === 'KRW' && krwRate.value != null
      ? krwRate.value
      : 1
    setCurrencyDisplay({ code: displayCurrency.value, rate })
  }, { immediate: true })

  /**
   * Initialize from the /me response. If account_currency is null,
   * the prompt should be shown.
   */
  function initFromUser(accountCurrency: string | null) {
    if (accountCurrency) {
      accountCurrencySet.value = true
      displayCurrency.value = accountCurrency as CurrencyCode
    } else {
      accountCurrencySet.value = false
      displayCurrency.value = 'USD'
    }
  }

  /** Persist the user's currency choice to the server. */
  async function saveAccountCurrency(currency: CurrencyCode) {
    await setAccountCurrency(currency)
    accountCurrencySet.value = true
    displayCurrency.value = currency

    // Pre-fetch the exchange rate if they chose KRW.
    if (currency === 'KRW' && krwRate.value === null) {
      await loadRate()
    }
  }

  /** Toggle between USD and KRW for display. */
  async function toggleDisplay() {
    if (displayCurrency.value === 'USD') {
      // Switching to KRW -- need the rate.
      if (krwRate.value === null) {
        await loadRate()
      }
      displayCurrency.value = 'KRW'
    } else {
      displayCurrency.value = 'USD'
    }
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
   * Convert a USD amount to the current display currency.
   * Returns the original value if display is USD or rate is unavailable.
   */
  function convert(usdAmount: number): number {
    if (displayCurrency.value === 'USD' || krwRate.value === null) {
      return usdAmount
    }
    return usdAmount * krwRate.value
  }

  /** Reset on logout. */
  function $reset() {
    displayCurrency.value = 'USD'
    accountCurrencySet.value = false
    krwRate.value = null
    rateLoading.value = false
  }

  return {
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
