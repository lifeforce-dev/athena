<template>
  <div class="fte-welcome">
    <div class="fte-card">
      <div class="fte-accent" />
      <p class="fte-brand">Athena</p>
      <p class="fte-title">{{ t('fte.welcome_title') }}</p>
      <p class="fte-desc">{{ t('fte.welcome_desc') }}</p>
      <p class="fte-hint">{{ t('fte.welcome_hint') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

// FteWelcome is the splash view in the demo/FTE flow and doesn't run
// useTabOnboarding, so it owns removing the CurrencyPrompt transition cover.
onMounted(() => {
  document.getElementById('demo-tour-cover')?.remove()
})
</script>

<style scoped>
.fte-welcome {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 48px);
  padding: 40px 20px;
}

.fte-card {
  text-align: center;
  max-width: 520px;
  padding: 48px 40px 40px;
}

.fte-accent {
  width: 48px;
  height: 2px;
  margin: 0 auto 32px;
  background: linear-gradient(90deg, var(--safe, #34D399), transparent);
}

.fte-brand {
  font-family: var(--font-mono, monospace);
  font-weight: 700;
  font-size: 42px;
  color: var(--bright, #E8ECF2);
  letter-spacing: 0.08em;
  margin: 0 0 12px;
}

.fte-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text, #B8BEC9);
  margin: 0 0 20px;
  letter-spacing: 0.02em;
}

.fte-desc {
  font-size: 14px;
  line-height: 1.8;
  color: var(--dim, #5A6378);
  margin: 0 0 28px;
}

.fte-hint {
  font-size: 13px;
  color: var(--safe, #34D399);
  letter-spacing: 0.04em;
  margin: 0;
}
</style>
