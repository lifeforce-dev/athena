import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  enrollTeller,
  selectTellerAccount,
  getTellerStatus,
  getTellerAccounts,
  disconnectTeller,
} from '@/api/teller'
import type {
  TellerEnrollRequest,
  TellerAccountOption,
  TellerStatusValue,
} from '@/types/teller'

const POLL_INTERVAL_MS = 2_000
const POLL_MAX_MS = 30_000

export const useTellerStore = defineStore('teller', () => {
  const isConnected = ref(false)
  const institutionName = ref<string | null>(null)
  const accountName = ref<string | null>(null)
  const lastSyncedAt = ref<string | null>(null)
  const status = ref<TellerStatusValue>('disconnected')
  const loading = ref(false)
  const error = ref<string | null>(null)

  /** Accounts returned by POST /enroll, awaiting user selection. */
  const pendingAccounts = ref<TellerAccountOption[]>([])

  const isSyncing = computed(() => status.value === 'syncing')
  const hasError = computed(() => status.value === 'error')
  const isAwaitingAccount = computed(() => status.value === 'awaiting_account')

  function applyStatus(
    connected: boolean,
    institution: string | null,
    account: string | null,
    synced: string | null,
    newStatus: TellerStatusValue,
  ) {
    isConnected.value = connected
    institutionName.value = institution
    accountName.value = account
    lastSyncedAt.value = synced
    status.value = newStatus
  }

  async function fetchStatus() {
    try {
      const res = await getTellerStatus()
      applyStatus(res.is_connected, res.institution_name, res.account_name, res.last_synced_at, res.status)
      error.value = null

      // Restore the account picker after a page reload.
      if (res.status === 'awaiting_account' && pendingAccounts.value.length === 0) {
        await resumeAccountSelection()
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch status'
    }
  }

  /**
   * Re-fetch selectable accounts for an enrollment stuck in awaiting_account.
   * Called automatically by fetchStatus() after a page reload.
   */
  async function resumeAccountSelection() {
    try {
      const res = await getTellerAccounts()
      institutionName.value = res.institution_name
      pendingAccounts.value = res.accounts
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to restore account list'
    }
  }

  /**
   * Start enrollment: POST /enroll → receive account list.
   * Caller should then present account picker and call confirmAccount().
   */
  async function enroll(data: TellerEnrollRequest) {
    loading.value = true
    error.value = null
    pendingAccounts.value = []
    try {
      const res = await enrollTeller(data)
      institutionName.value = res.institution_name
      status.value = res.status
      pendingAccounts.value = res.accounts
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Enrollment failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * Confirm account selection, then poll until status leaves 'syncing'.
   */
  async function confirmAccount(accountId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await selectTellerAccount({ account_id: accountId })
      applyStatus(res.is_connected, res.institution_name, res.account_name, res.last_synced_at, res.status)
      pendingAccounts.value = []

      if (res.status === 'syncing') {
        await pollUntilResolved()
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Account selection failed'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function disconnect() {
    loading.value = true
    error.value = null
    try {
      await disconnectTeller()
      applyStatus(false, null, null, null, 'disconnected')
      pendingAccounts.value = []
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Disconnect failed'
    } finally {
      loading.value = false
    }
  }

  async function pollUntilResolved() {
    const deadline = Date.now() + POLL_MAX_MS
    while (Date.now() < deadline) {
      await sleep(POLL_INTERVAL_MS)
      await fetchStatus()
      if (status.value !== 'syncing') return
    }
    // Timed out — leave status as syncing; next manual fetchStatus will catch up.
  }

  return {
    isConnected,
    institutionName,
    accountName,
    lastSyncedAt,
    status,
    loading,
    error,
    pendingAccounts,
    isSyncing,
    hasError,
    isAwaitingAccount,
    fetchStatus,
    enroll,
    confirmAccount,
    disconnect,
  }
})

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
