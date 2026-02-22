<template>
  <Teleport to="body">
    <div class="currency-overlay">
      <div class="currency-modal">
        <h2 class="cm-title">{{ t('currency_prompt.title') }}</h2>
        <p class="cm-desc">
          {{ t('currency_prompt.desc') }}
        </p>

        <div class="cm-options">
          <button
            v-for="opt in options"
            :key="opt.code"
            class="cm-opt"
            :class="{ selected: selected === opt.code }"
            @click="selectCurrency(opt.code)"
          >
            <span class="cm-opt-symbol">{{ opt.symbol }}</span>
            <span class="cm-opt-label">{{ opt.label }}</span>
          </button>
        </div>

        <Transition name="cm-info">
          <div v-if="selected" class="cm-lang-info">
            <span class="cm-lang-text">{{ t('currency_prompt.lang_info') }}</span>
            <span class="cm-lang-anchor">
              <button class="cm-lang-pick" @click="langOpen = !langOpen">
                {{ chosenLangLabel }}
                <span class="cm-lang-caret">&#9662;</span>
              </button>
              <Transition name="cm-info">
                <div v-if="langOpen" class="cm-lang-dropdown">
                  <button
                    v-for="(label, code) in languageOptions"
                    :key="code"
                    class="cm-lang-item"
                    :class="{ active: chosenLang === code }"
                    @click="pickLang(code)"
                  >
                    {{ label }}
                  </button>
                </div>
              </Transition>
            </span>
          </div>
        </Transition>

        <button class="cm-confirm" :disabled="!selected || saving" @click="confirm">
          {{ saving ? t('currency_prompt.saving') : t('currency_prompt.continue') }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCurrencyStore } from '@/stores/currency'
import { useLanguageStore } from '@/stores/language'
import { demoTourActive } from '@/stores/demoTour'
import { type CurrencyCode, CURRENCIES, CURRENCY_CODES, LANGUAGE_LABELS } from '@/config/currencies'
import { useI18n } from '@/composables/useI18n'
import { setLanguage } from '@/api/auth'

const { t } = useI18n()
const currency = useCurrencyStore()
const language = useLanguageStore()
const emit = defineEmits<{ done: [] }>()

const selected = ref<CurrencyCode | null>(null)
const saving = ref(false)
const langOpen = ref(false)

// Language override — null means "use the currency's default."
const langOverride = ref<string | null>(null)

const options = CURRENCY_CODES.map((code) => ({
  code,
  symbol: CURRENCIES[code].symbol,
  label: `${CURRENCIES[code].name} (${code})`,
}))

const languageOptions = LANGUAGE_LABELS

const defaultLangForCurrency = computed(() =>
  selected.value ? CURRENCIES[selected.value].defaultLang : 'en_US',
)

const chosenLang = computed(() => langOverride.value ?? defaultLangForCurrency.value)
const chosenLangLabel = computed(() => LANGUAGE_LABELS[chosenLang.value] ?? chosenLang.value)

function selectCurrency(code: CurrencyCode) {
  selected.value = code
  // Reset language override when switching currencies.
  langOverride.value = null
  langOpen.value = false
}

function pickLang(code: string) {
  langOverride.value = code === defaultLangForCurrency.value ? null : code
  langOpen.value = false
}

async function confirm() {
  if (!selected.value || saving.value) return
  saving.value = true

  console.info('[TourDebug][CurrencyPrompt] Confirm clicked', {
    selectedCurrency: selected.value,
    hasLanguageOverride: !!langOverride.value,
    languageOverride: langOverride.value,
  })

  // Set BEFORE the await -- saveAccountCurrency flips accountCurrencySet,
  // which triggers Vue reactivity to mount DashboardView.  If demoTourActive
  // is not already true at that point, the dashboard loads real (empty) data.
  demoTourActive.value = true

  // Inject an opaque cover so the dashboard never flashes while the
  // CurrencyPrompt unmounts and the splash overlay takes over.
  const cover = document.createElement('div')
  cover.id = 'demo-tour-cover'
  cover.style.cssText = 'position:fixed;inset:0;z-index:99999;background:var(--bg,#06080C);'
  document.body.appendChild(cover)

  try {
    await currency.saveAccountCurrency(selected.value)

    // If the user overrode the language, persist it immediately.
    if (langOverride.value) {
      console.info('[TourDebug][CurrencyPrompt] Persisting language override', {
        language: langOverride.value,
      })
      await setLanguage(langOverride.value)
      language.initFromUser(langOverride.value)
    }

    console.info('[TourDebug][CurrencyPrompt] Currency flow complete, emitting done')
    emit('done')
  } catch (err) {
    // Save failed — roll back the optimistic flag so real data loads normally.
    demoTourActive.value = false
    console.error('[CurrencyPrompt] Save failed, rolled back demoTourActive', err)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.currency-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
}

.currency-modal {
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 32px 36px;
  max-width: 440px;
  width: 100%;
  text-align: center;
}

.cm-title {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  color: var(--bright);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin: 0 0 12px;
}

.cm-desc {
  font-size: 12px;
  color: var(--dim);
  line-height: 1.5;
  margin: 0 0 24px;
}

.cm-options {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 10px;
  margin-bottom: 24px;
}

.cm-opt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--dim);
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}

.cm-opt:hover {
  border-color: var(--text);
  color: var(--text);
}

.cm-opt.selected {
  border-color: var(--income);
  color: var(--bright);
}

.cm-opt-symbol {
  font-size: 18px;
  font-weight: 700;
}

.cm-opt-label {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.cm-confirm {
  width: 100%;
  padding: 10px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--bg);
  background: var(--income);
  border: none;
  cursor: pointer;
  transition: opacity 0.2s;
}

.cm-confirm:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.cm-confirm:not(:disabled):hover {
  opacity: 0.85;
}

/* Language info bar */
.cm-lang-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 10px 14px;
  margin-bottom: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  font-size: 11px;
  color: var(--dim);
}

.cm-lang-text {
  white-space: nowrap;
}

.cm-lang-pick {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: none;
  border: none;
  border-bottom: 1px dashed var(--income);
  color: var(--income);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  transition: opacity 0.2s;
}

.cm-lang-pick:hover {
  opacity: 0.75;
}

.cm-lang-caret {
  font-size: 8px;
  opacity: 0.6;
}

.cm-lang-anchor {
  position: relative;
}

.cm-lang-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg);
  border: 1px solid var(--border);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
  z-index: 10;
  display: flex;
  flex-direction: column;
  min-width: 140px;
}

.cm-lang-item {
  padding: 8px 14px;
  background: none;
  border: none;
  color: var(--dim);
  font-size: 11px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.cm-lang-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text);
}

.cm-lang-item.active {
  color: var(--income);
  font-weight: 600;
}

/* Transition for info bar */
.cm-info-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.cm-info-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.cm-info-enter-from {
  opacity: 0;
  transform: translateY(-6px);
}

.cm-info-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
