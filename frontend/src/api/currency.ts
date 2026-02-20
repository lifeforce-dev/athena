import { api } from './client'

export interface SetCurrencyResponse {
  account_currency: string
}

export interface ExchangeRateResponse {
  base: string
  target: string
  rate: number
}

/** Set the user's account currency (USD or KRW). */
export const setAccountCurrency = (currency: string) =>
  api.patch<SetCurrencyResponse>('/currency/account', { currency })

export interface SetDisplayCurrencyResponse {
  display_currency: string
}

/** Persist the user's active display currency toggle. */
export const setDisplayCurrency = (currency: string) =>
  api.patch<SetDisplayCurrencyResponse>('/currency/display', { currency })

/** Fetch the USD -> target exchange rate (cached server-side for 1hr). */
export const fetchExchangeRate = (target: string = 'KRW') =>
  api.get<ExchangeRateResponse>(`/currency/rate?target=${target}`)
