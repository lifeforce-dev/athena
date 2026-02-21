import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { setAccountCurrency, setDisplayCurrency as apiSetDisplayCurrency, fetchExchangeRate } from '@/api/currency'
import { setCurrencyDisplay } from '@/utils/format'
import { type CurrencyCode, CURRENCY_CODES, getCurrencyConfig } from '@/config/currencies'

export type { CurrencyCode }

export const useCurrencyStore = defineStore('currency', () => {
  /** The user's real-world currency (what's stored in the DB). */
  const accountCurrency = ref<CurrencyCode>('USD')

  /** The currency currently displayed in the UI and used for input. */
  const displayCurrency = ref<CurrencyCode>('USD')

  /** Whether the user has set account_currency on the server. */
  const accountCurrencySet = ref(false)

  /** Cached exchange rates: "BASE:TARGET" -> rate. */
  const rates = ref<Map<string, number>>(new Map())

  /** True while we're fetching an exchange rate. */
  const rateLoading = ref(false)

  const isConverted = computed(() => displayCurrency.value !== accountCurrency.value)

  /** Get the cached rate for account -> display. Returns null if not loaded. */
  function currentRate(): number | null {
    if (accountCurrency.value === displayCurrency.value) {
      return 1
    }

    return rates.value.get(`${accountCurrency.value}:${displayCurrency.value}`) ?? null
  }

  // Push display state into the format layer whenever it changes.
  watch([accountCurrency, displayCurrency, rates], () => {
    const rate = currentRate() ?? 1
    setCurrencyDisplay({ code: displayCurrency.value, rate })
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
  }

  /** Toggle to the next display currency in the supported list. */
  async function toggleDisplay() {
    const currentIndex = CURRENCY_CODES.indexOf(displayCurrency.value)
    const nextIndex = (currentIndex + 1) % CURRENCY_CODES.length
    const newCurrency = CURRENCY_CODES[nextIndex]

    // Load the rate for acct -> new currency if needed.
    if (newCurrency !== accountCurrency.value) {
      const key = `${accountCurrency.value}:${newCurrency}`

      if (!rates.value.has(key)) {
        try {
          await loadRate(accountCurrency.value, newCurrency)
        } catch {
          console.error('Failed to fetch exchange rate')
          return
        }
      }
    }

    displayCurrency.value = newCurrency
    await apiSetDisplayCurrency(newCurrency)
  }

  /** Fetch and cache an exchange rate between any two currencies. */
  async function loadRate(base: string, target: string) {
    if (base === target) {
      return
    }

    const key = `${base}:${target}`

    if (rateLoading.value) {
      return
    }

    rateLoading.value = true
    try {
      const resp = await fetchExchangeRate(base, target)
      const updated = new Map(rates.value)
      updated.set(key, resp.rate)
      rates.value = updated
    } finally {
      rateLoading.value = false
    }
  }

  /**
   * Convert an account-currency amount to the current display currency.
   * Returns the original value if currencies match or rate is unavailable.
   */
  function convert(amount: number): number {
    const rate = currentRate()

    if (rate === null || rate === 1) {
      return amount
    }

    return amount * rate
  }

  /** Reset on logout. */
  function $reset() {
    accountCurrency.value = 'USD'
    displayCurrency.value = 'USD'
    accountCurrencySet.value = false
    rates.value = new Map()
    rateLoading.value = false
  }

  return {
    accountCurrency,
    displayCurrency,
    accountCurrencySet,
    rates,
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
