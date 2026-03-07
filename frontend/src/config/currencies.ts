/**
 * Currency configuration — single source of truth.
 *
 * Adding a new currency:
 *  1. Add an entry here.
 *  2. Add the code to ALLOWED_CURRENCIES in app/routers/currency.py.
 *  3. (Optional) Add a matching locale file in src/locales/.
 */

export const CURRENCIES = {
  USD: { symbol: '$', name: 'US Dollar', decimals: 2, defaultLang: 'en_US' },
  KRW: { symbol: '\u20A9', name: 'Korean Won', decimals: 0, defaultLang: 'ko_KR' },
  JPY: { symbol: '\u00A5', name: 'Japanese Yen', decimals: 0, defaultLang: 'ja_JP' },
  EUR: { symbol: '\u20AC', name: 'Euro', decimals: 2, defaultLang: 'en_US' },
  GBP: { symbol: '\u00A3', name: 'British Pound', decimals: 2, defaultLang: 'en_US' },
  CNY: { symbol: '\u00A5', name: 'Chinese Yuan', decimals: 2, defaultLang: 'zh_CN' },
  BRL: { symbol: 'R$', name: 'Brazilian Real', decimals: 2, defaultLang: 'pt_BR' },
} as const

export type CurrencyCode = keyof typeof CURRENCIES

/** All supported currency codes as an array. */
export const CURRENCY_CODES = Object.keys(CURRENCIES) as CurrencyCode[]

/** Get config for a currency code, or USD as fallback. */
export function getCurrencyConfig(code: string) {
  return CURRENCIES[code as CurrencyCode] ?? CURRENCIES.USD
}

/**
 * Human-readable language names keyed by locale code.
 * Used in the currency prompt to preview the default language choice.
 */
export const LANGUAGE_LABELS: Record<string, string> = {
  en_US: 'English',
  ko_KR: '\ud55c\uad6d\uc5b4',
  ja_JP: '\u65e5\u672c\u8a9e',
  zh_CN: '\u4e2d\u6587',
  pt_BR: 'Portugu\u00eas',
}

/** All locale codes that have (or will have) translation support. */
export const AVAILABLE_LOCALES = Object.keys(LANGUAGE_LABELS)

/**
 * Locale codes with actual translation files.
 * Only these should appear in the settings language picker.
 */
export const IMPLEMENTED_LOCALES: Record<string, string> = {
  en_US: 'English',
  ko_KR: '\ud55c\uad6d\uc5b4',
}
