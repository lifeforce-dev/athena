<template>
  <Teleport to="body">
    <div v-if="showAccountPicker" class="tc-overlay">
      <div class="tc-modal">
        <div class="tc-title">Select an account</div>
        <p class="tc-subtitle">Choose which account Athena should track:</p>

        <div v-if="teller.loading" class="tc-loading">Connecting...</div>

        <div v-else class="tc-accounts">
          <button
            v-for="acct in teller.pendingAccounts"
            :key="acct.id"
            class="tc-account"
            :class="{ selected: selectedAccountId === acct.id }"
            @click="selectedAccountId = acct.id"
          >
            <span class="tc-acct-name">{{ acct.name }}</span>
            <span class="tc-acct-meta">{{ acct.subtype }} · {{ acct.currency }}</span>
            <span class="tc-acct-inst">{{ acct.institution_name }}</span>
          </button>
        </div>

        <div v-if="teller.error" class="tc-error">{{ teller.error }}</div>

        <div class="tc-actions">
          <button class="btn btn-cancel" @click="handleCancel">Cancel</button>
          <button
            class="btn btn-save"
            :disabled="!selectedAccountId || teller.loading"
            @click="handleConfirm"
          >
            {{ teller.loading ? 'Connecting...' : 'Connect' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useTellerStore } from '@/stores/teller'

const TELLER_APP_ID = import.meta.env.VITE_TELLER_APP_ID ?? ''
const TELLER_ENVIRONMENT = import.meta.env.VITE_TELLER_ENVIRONMENT ?? 'sandbox'

const teller = useTellerStore()
const selectedAccountId = ref<string | null>(null)

const showAccountPicker = computed(
  () => teller.pendingAccounts.length > 0,
)

const emit = defineEmits<{
  connected: []
  cancelled: []
}>()

function loadTellerScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.getElementById('teller-connect-script')) return resolve()
    const script = document.createElement('script')
    script.id = 'teller-connect-script'
    script.src = 'https://cdn.teller.io/connect/connect.js'
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load Teller Connect SDK'))
    document.head.appendChild(script)
  })
}

/**
 * Open the Teller Connect widget. Called by the parent (NavBar).
 * On success, enrolls and shows the account picker.
 */
async function open() {
  teller.error = null
  try {
    await loadTellerScript()
  } catch {
    teller.error = 'Could not load bank connection. Please try again.'
    return
  }

  const win = window as any
  if (!win.TellerConnect) {
    teller.error = 'Bank connection unavailable.'
    return
  }

  const tellerConnect = win.TellerConnect.setup({
    applicationId: TELLER_APP_ID,
    environment: TELLER_ENVIRONMENT,
    onSuccess: async (enrollment: any) => {
      try {
        await teller.enroll({
          access_token: enrollment.accessToken,
          enrollment_id: enrollment.enrollment.id,
          institution: enrollment.enrollment.institution.name,
        })
      } catch {
        // Error already set on the store.
      }
    },
    onFailure: (failure: any) => {
      teller.error = failure?.message ?? 'Bank connection failed'
    },
    onExit: () => {
      if (!teller.pendingAccounts.length && !teller.error) {
        emit('cancelled')
      }
    },
  })
  tellerConnect.open()
}

async function handleConfirm() {
  if (!selectedAccountId.value) return
  try {
    await teller.confirmAccount(selectedAccountId.value)
    selectedAccountId.value = null
    emit('connected')
  } catch {
    // Error already set on the store.
  }
}

function handleCancel() {
  teller.pendingAccounts = []
  selectedAccountId.value = null
  emit('cancelled')
}

defineExpose({ open })
</script>

<style scoped>
.tc-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.tc-modal {
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 28px 32px;
  width: 400px;
  max-width: 90vw;
  max-height: 80vh;
  overflow-y: auto;
  backdrop-filter: blur(24px);
}

.tc-title {
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--bright);
  margin-bottom: 6px;
}

.tc-subtitle {
  font-size: 11px;
  color: var(--dim);
  margin-bottom: 16px;
}

.tc-accounts {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}

.tc-account {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 14px;
  background: none;
  border: 1px solid var(--border);
  color: var(--text);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, color 0.15s;
}

.tc-account:hover {
  border-color: var(--dim);
}

.tc-account.selected {
  border-color: var(--safe);
  color: var(--bright);
}

.tc-acct-name {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.tc-acct-meta {
  font-size: 10px;
  color: var(--dim);
  text-transform: capitalize;
}

.tc-acct-inst {
  font-size: 9px;
  color: var(--dim);
  opacity: 0.7;
}

.tc-loading {
  font-size: 11px;
  color: var(--dim);
  padding: 16px 0;
  text-align: center;
}

.tc-error {
  font-size: 10px;
  color: var(--danger);
  margin-bottom: 12px;
}

.tc-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 8px 16px;
  cursor: pointer;
  transition: opacity 0.15s;
}

.btn:disabled {
  opacity: 0.35;
  cursor: default;
}

.btn-cancel {
  background: none;
  border: 1px solid var(--border);
  color: var(--dim);
}

.btn-cancel:hover:not(:disabled) {
  color: var(--text);
  border-color: var(--dim);
}

.btn-save {
  background: var(--safe);
  border: none;
  color: var(--bg);
}

.btn-save:hover:not(:disabled) {
  opacity: 0.85;
}
</style>
