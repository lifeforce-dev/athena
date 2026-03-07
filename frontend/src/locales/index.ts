/**
 * Locale registry.
 *
 * The base locale (en_US) is bundled eagerly so the app never shows raw keys.
 * Additional locales are lazily imported when needed.
 */

import en_US, { type LocaleEntry } from './en_US'

/** Flat text-only locale (used by every locale except the base). */
export type FlatLocale = Record<string, string>

/** The base locale with context annotations. */
export type BaseLocale = Record<string, LocaleEntry>

export type SupportedLocale = 'en_US' | 'ko_KR'

const LOCALE_LOADERS: Record<string, () => Promise<{ default: FlatLocale }>> = {
  ko_KR: () => import('./ko_KR'),
}

/** Already-resolved locales. en_US is always available. */
const resolved = new Map<string, FlatLocale>()

// Pre-flatten en_US so the lookup path is identical for all locales.
const flatEnUS: FlatLocale = Object.fromEntries(
  Object.entries(en_US).map(([key, entry]) => [key, entry.text]),
)
resolved.set('en_US', flatEnUS)

/**
 * Get the flat text map for a locale, loading it lazily if needed.
 * Falls back to en_US if the locale is unknown or fails to load.
 */
export async function loadLocale(locale: string): Promise<FlatLocale> {
  if (resolved.has(locale)) {
    return resolved.get(locale)!
  }

  const loader = LOCALE_LOADERS[locale]

  if (!loader) {
    console.warn(`[i18n] Unknown locale "${locale}", falling back to en_US`)
    return flatEnUS
  }

  try {
    const mod = await loader()
    resolved.set(locale, mod.default)
    return mod.default
  } catch (error) {
    console.error(`[i18n] Failed to load locale "${locale}"`, error)
    return flatEnUS
  }
}

/**
 * Synchronous lookup. Returns the flat map if already loaded, otherwise en_US.
 * Callers that need a fresh locale should await `loadLocale()` first.
 */
export function getLocaleSync(locale: string): FlatLocale {
  return resolved.get(locale) ?? flatEnUS
}

/** Convenience: the base-language flat map, always available. */
export const baseLocale = flatEnUS
