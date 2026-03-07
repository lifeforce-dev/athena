import { computed } from 'vue'
import IntlMessageFormat from 'intl-messageformat'
import { useLanguageStore } from '@/stores/language'

/**
 * Composable that exposes a reactive `t()` helper for translating UI strings.
 *
 * Basic usage:
 *   const { t } = useI18n()
 *   t('hero.current_balance')             // "Current Balance"
 *   t('hero.days_projected_lbl')              // "days projected"
 *
 * ICU plurals work automatically:
 *   t('shortfall.at_risk', { count: 3 })  // "3 commitments at risk"
 */
export function useI18n() {
  const lang = useLanguageStore()

  // Light cache so we only compile each ICU pattern once per locale.
  const cache = new Map<string, IntlMessageFormat>()

  const messages = computed(() => lang.messages)

  function t(key: string, params?: Record<string, string | number>): string {
    const raw = messages.value[key]

    if (raw === undefined) {
      console.warn(`[i18n] Missing key: "${key}"`)
      return key
    }

    // Fast path: no params, no ICU syntax needed.
    if (!params) {
      return raw
    }

    // Check cache.
    const cacheKey = `${lang.locale}::${key}`
    let fmt = cache.get(cacheKey)

    if (!fmt) {
      fmt = new IntlMessageFormat(raw, lang.locale.replace('_', '-'))
      cache.set(cacheKey, fmt)
    }

    return fmt.format(params) as string
  }

  return { t }
}
