import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { loadLocale, getLocaleSync, type FlatLocale } from '@/locales'

export const useLanguageStore = defineStore('language', () => {
  const locale = ref('en_US')
  const messages = ref<FlatLocale>(getLocaleSync('en_US'))

  /** Hydrate from user profile on login. */
  function initFromUser(accountLanguage: string | null) {
    const lang = accountLanguage ?? 'en_US'

    if (lang !== locale.value) {
      locale.value = lang
    }
  }

  // Reload message bundle when locale changes.
  watch(locale, async (next) => {
    messages.value = await loadLocale(next)
  })

  return { locale, messages, initFromUser }
})
