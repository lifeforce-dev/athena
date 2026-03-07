<template>
  <Teleport to="body">
    <!-- Pre-flow error modal (SDK not configured / can't load) -->
    <div v-if="showErrorModal" class="tc-overlay" @click.self="dismissError">
      <div class="tc-modal">
        <div class="tc-title">Connection unavailable</div>
        <p class="tc-subtitle">Internal error. Please try again later.</p>
        <div class="tc-actions">
          <button class="btn btn-cancel" @click="dismissError">Close</button>
        </div>
      </div>
    </div>

    <!-- In-flow modal (account picker OR error during connection) -->
    <div v-if="showFlowModal" class="tc-overlay">
      <div class="tc-modal">
        <!-- Error replaces picker content when something goes wrong mid-flow -->
        <template v-if="flowError">
          <div class="tc-title">Connection failed</div>
          <div class="tc-error">{{ flowError }}</div>
          <div class="tc-actions">
            <button class="btn btn-cancel" @click="dismissFlow">Close</button>
          </div>
        </template>

        <template v-else>
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
        </template>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useTellerStore } from '@/stores/teller'
import { getTellerNonce } from '@/api/teller'

const TELLER_APP_ID = import.meta.env.VITE_TELLER_APP_ID ?? ''
const TELLER_ENVIRONMENT = import.meta.env.VITE_TELLER_ENVIRONMENT ?? 'sandbox'

const teller = useTellerStore()
const selectedAccountId = ref<string | null>(null)

const showErrorModal = ref(false)
const showFlowModal = ref(false)
const flowError = ref<string | null>(null)

/** Cached nonce + HMAC for the current Teller Connect session. */
let currentNonce = ''
let currentNonceMac = ''

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
  flowError.value = null

  if (!TELLER_APP_ID) {
    console.error('VITE_TELLER_APP_ID is not set — bank connection unavailable')
    showErrorModal.value = true
    return
  }

  try {
    await loadTellerScript()
  } catch (err) {
    console.error('Failed to load Teller Connect SDK:', err)
    showErrorModal.value = true
    return
  }

  // Fetch a server-generated nonce for token signing verification.
  try {
    const nonceRes = await getTellerNonce()
    currentNonce = nonceRes.nonce
    currentNonceMac = nonceRes.nonce_mac
  } catch (err) {
    console.error('Failed to fetch enrollment nonce:', err)
    showErrorModal.value = true
    return
  }

  const win = window as any
  if (!win.TellerConnect) {
    console.error('TellerConnect global not found after script loaded')
    showErrorModal.value = true
    return
  }

  const tellerConnect = win.TellerConnect.setup({
    applicationId: TELLER_APP_ID,
    environment: TELLER_ENVIRONMENT,
    selectAccount: 'disabled',
    nonce: currentNonce,
    onSuccess: async (enrollment: any) => {
      showFlowModal.value = true
      try {
        await teller.enroll({
          access_token: enrollment.accessToken,
          enrollment_id: enrollment.enrollment.id,
          institution: enrollment.enrollment.institution.name,
          signatures: enrollment.signatures ?? [],
          teller_user_id: enrollment.user?.id ?? '',
          nonce: currentNonce,
          nonce_mac: currentNonceMac,
        })
      } catch {
        flowError.value = teller.error ?? 'Something went wrong connecting your bank.'
      }
    },
    onFailure: (failure: any) => {
      flowError.value = failure?.message ?? 'Bank connection failed. Please try again.'
      showFlowModal.value = true
    },
    onExit: () => {
      if (!showFlowModal.value) {
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
    showFlowModal.value = false
    emit('connected')
  } catch {
    flowError.value = teller.error ?? 'Failed to connect the selected account.'
  }
}

async function handleCancel() {
  // Clean up the backend enrollment so it doesn't strand in awaiting_account.
  await teller.disconnect()
  selectedAccountId.value = null
  showFlowModal.value = false
  flowError.value = null
  emit('cancelled')
}

async function dismissFlow() {
  if (teller.isAwaitingAccount) {
    await teller.disconnect()
  }
  teller.pendingAccounts = []
  selectedAccountId.value = null
  showFlowModal.value = false
  flowError.value = null
  teller.error = null
}

function dismissError() {
  showErrorModal.value = false
}

defineExpose({ open })

// Resume the account picker after a page reload when the store
// re-fetches accounts for an awaiting_account enrollment.
watch(
  () => teller.isAwaitingAccount && teller.pendingAccounts.length > 0,
  (shouldShow) => {
    if (shouldShow && !showFlowModal.value) {
      showFlowModal.value = true
    }
  },
)
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
