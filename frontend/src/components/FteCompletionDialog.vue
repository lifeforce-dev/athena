<template>
  <Teleport to="body">
    <div class="fte-overlay">
      <div class="fte-dialog">
        <div class="fte-dialog-accent" />
        <p class="fte-dialog-title">{{ t('fte.complete_title') }}</p>
        <p class="fte-dialog-desc">{{ t('fte.complete_desc') }}</p>
        <button class="fte-dialog-btn" @click="handleFinish">
          {{ t('fte.complete_button') }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useI18n } from '@/composables/useI18n'
import { endFte } from '@/stores/fte'
import { demoTourActive } from '@/stores/demoTour'

const { t } = useI18n()

function handleFinish() {
  endFte()
  demoTourActive.value = false
  window.location.replace('/')
}
</script>

<style scoped>
.fte-overlay {
  position: fixed;
  inset: 0;
  z-index: 100000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(6px);
}

.fte-dialog {
  text-align: center;
  max-width: 380px;
  padding: 40px 36px 32px;
  background: var(--panel, #0D1117);
  border: 1px solid var(--border, #1C2333);
  border-radius: 8px;
}

.fte-dialog-accent {
  width: 40px;
  height: 2px;
  margin: 0 auto 24px;
  background: linear-gradient(90deg, var(--safe, #34D399), transparent);
}

.fte-dialog-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--bright, #E8ECF2);
  margin: 0 0 12px;
}

.fte-dialog-desc {
  font-size: 12px;
  line-height: 1.7;
  color: var(--dim, #5A6378);
  margin: 0 0 28px;
}

.fte-dialog-btn {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--bg, #06080C);
  background: var(--safe, #34D399);
  border: none;
  border-radius: 4px;
  padding: 10px 28px;
  cursor: pointer;
  transition: opacity 0.2s;
}

.fte-dialog-btn:hover {
  opacity: 0.85;
}
</style>
