<template>
  <Teleport to="body">
    <div class="onboarding-overlay">
      <div class="onboarding-modal">
        <div class="om-brand">{{ t('login.brand') }}</div>
        <h2 class="om-title">{{ t('onboarding.title') }}</h2>
        <p class="om-desc">{{ t('onboarding.desc') }}</p>

        <div class="om-options">
          <button class="om-opt om-opt-demo" :disabled="loading" @click="startDemo">
            <span class="om-opt-icon">&#9654;</span>
            <span class="om-opt-text">
              <span class="om-opt-label">{{ t('onboarding.demo_label') }}</span>
              <span class="om-opt-hint">{{ t('onboarding.demo_hint') }}</span>
            </span>
          </button>
          <button class="om-opt om-opt-setup" @click="startSetup">
            <span class="om-opt-icon">&#9881;</span>
            <span class="om-opt-text">
              <span class="om-opt-label">{{ t('onboarding.setup_label') }}</span>
              <span class="om-opt-hint">{{ t('onboarding.setup_hint') }}</span>
            </span>
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from '@/composables/useI18n'
import { useAuthStore } from '@/stores/auth'
import { dismissModal } from '@/api/auth'
import { api } from '@/api/client'

const MODAL_KEY = 'onboarding_demo'

const { t } = useI18n()
const auth = useAuthStore()
const loading = ref(false)

const emit = defineEmits<{ dismiss: [] }>()

async function persistDismiss() {
  if (auth.user && !(auth.user.dismissed_modals ?? []).includes(MODAL_KEY)) {
    try {
      await dismissModal(MODAL_KEY)
      auth.user.dismissed_modals = [...(auth.user.dismissed_modals ?? []), MODAL_KEY]
    } catch {
      // Non-critical.
    }
  }
}

async function startDemo() {
  loading.value = true
  await persistDismiss()

  try {
    // Start demo session (sets cookie with demo user credentials).
    await api.post<void>('/auth/demo-start')
    // Full reload to pick up the new session and demo data.
    window.location.href = '/?tour=dashboard'
  } catch (err) {
    console.error('Demo start failed:', err)
    loading.value = false
  }
}

async function startSetup() {
  await persistDismiss()
  emit('dismiss')
}
</script>

<style scoped>
.onboarding-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(10px);
}

.onboarding-modal {
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 40px 44px;
  max-width: 440px;
  width: 100%;
  text-align: center;
}

.om-brand {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--dim);
  margin-bottom: 16px;
}

.om-title {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 700;
  color: var(--bright);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 0 0 12px;
}

.om-desc {
  font-size: 12px;
  color: var(--dim);
  line-height: 1.6;
  margin: 0 0 28px;
  max-width: 360px;
  margin-left: auto;
  margin-right: auto;
}

.om-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.om-opt {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--dim);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.2s, color 0.2s;
}

.om-opt:hover {
  border-color: var(--text);
  color: var(--text);
}

.om-opt:disabled {
  opacity: 0.5;
  cursor: wait;
}

.om-opt-demo:hover {
  border-color: var(--income);
}

.om-opt-icon {
  font-size: 18px;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.om-opt-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.om-opt-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--bright);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.om-opt-hint {
  font-size: 11px;
  color: var(--dim);
  line-height: 1.4;
}
</style>
