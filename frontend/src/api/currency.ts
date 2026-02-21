import { api } from './client'

export interface SetCurrencyResponse {
  account_currency: string
}

export interface ExchangeRateResponse {
  base: string
  target: string
  rate: number
}

/** Set the user's account currency. */
export const setAccountCurrency = (currency: string) =>
  api.patch<SetCurrencyResponse>('/currency/account', { currency })

export interface SetDisplayCurrencyResponse {
  display_currency: string
}

/** Persist the user's active display currency toggle. */
export const setDisplayCurrency = (currency: string) =>
  api.patch<SetDisplayCurrencyResponse>('/currency/display', { currency })

/** Fetch the exchange rate between any two supported currencies (1hr server cache). */
export const fetchExchangeRate = (base: string, target: string) =>
  api.get<ExchangeRateResponse>(`/currency/rate?base=${base}&target=${target}`)
