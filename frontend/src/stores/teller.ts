import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  enrollTeller,
  selectTellerAccount,
  getTellerStatus,
  getTellerAccounts,
  disconnectTeller,
  refreshBalance as apiRefreshBalance,
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
  const lastManualRefreshAt = ref<string | null>(null)
  const status = ref<TellerStatusValue>('disconnected')
  const loading = ref(false)
  const error = ref<string | null>(null)

  /** Cooldown duration in seconds (sent by server). */
  const cooldownSeconds = ref(3600)

  /** Accounts returned by POST /enroll, awaiting user selection. */
  const pendingAccounts = ref<TellerAccountOption[]>([])

  const isSyncing = computed(() => status.value === 'syncing')
  const hasError = computed(() => status.value === 'error')
  const isAwaitingAccount = computed(() => status.value === 'awaiting_account')

  /** Seconds remaining on the manual refresh cooldown (reactive, ticks down). */
  const cooldownRemaining = ref(0)
  let cooldownTimer: ReturnType<typeof setInterval> | null = null

  function startCooldownTicker() {
    stopCooldownTicker()
    cooldownTimer = setInterval(() => {
      if (cooldownRemaining.value > 0) {
        cooldownRemaining.value--
      } else {
        stopCooldownTicker()
      }
    }, 1000)
  }

  function stopCooldownTicker() {
    if (cooldownTimer !== null) {
      clearInterval(cooldownTimer)
      cooldownTimer = null
    }
  }

  /** Recompute cooldownRemaining from the server timestamp. */
  function syncCooldown(refreshedAt: string | null, cdSeconds: number = 3600) {
    cooldownSeconds.value = cdSeconds
    if (!refreshedAt) {
      cooldownRemaining.value = 0
      stopCooldownTicker()
      return
    }
    const elapsed = (Date.now() - new Date(refreshedAt).getTime()) / 1000
    const remaining = Math.max(0, Math.ceil(cdSeconds - elapsed))
    cooldownRemaining.value = remaining
    if (remaining > 0) {
      startCooldownTicker()
    } else {
      stopCooldownTicker()
    }
  }

  function applyStatus(
    connected: boolean,
    institution: string | null,
    account: string | null,
    synced: string | null,
    newStatus: TellerStatusValue,
    manualRefresh: string | null = null,
  ) {
    isConnected.value = connected
    institutionName.value = institution
    accountName.value = account
    lastSyncedAt.value = synced
    lastManualRefreshAt.value = manualRefresh
    status.value = newStatus
    syncCooldown(manualRefresh)
  }

  async function fetchStatus() {
    try {
      const res = await getTellerStatus()
      applyStatus(res.is_connected, res.institution_name, res.account_name, res.last_synced_at, res.status, res.last_manual_refresh_at)
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
      applyStatus(res.is_connected, res.institution_name, res.account_name, res.last_synced_at, res.status, res.last_manual_refresh_at)
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
      applyStatus(false, null, null, null, 'disconnected', null)
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

  /** Refreshing flag (distinct from loading, which is for enrollment ops). */
  const refreshing = ref(false)

  /**
   * Manually refresh the balance from the connected bank.
   * Returns the new balance as a number, or null if the request failed.
   */
  async function doRefreshBalance(): Promise<number | null> {
    if (cooldownRemaining.value > 0 || refreshing.value) return null
    refreshing.value = true
    error.value = null
    try {
      const res = await apiRefreshBalance()
      lastManualRefreshAt.value = res.cooldown_started_at
      syncCooldown(res.cooldown_started_at, res.cooldown_seconds)
      return parseFloat(res.balance)
    } catch (err: unknown) {
      // If server says we're on cooldown (429), sync from the error body.
      if (err && typeof err === 'object' && 'status' in err && (err as { status: number }).status === 429) {
        try {
          const body = (err as { body?: { cooldown_started_at?: string; cooldown_seconds?: number } }).body
          if (body?.cooldown_started_at) {
            syncCooldown(body.cooldown_started_at, body.cooldown_seconds ?? 3600)
          }
        } catch { /* ignore parse error */ }
      }
      error.value = err instanceof Error ? err.message : 'Refresh failed'
      return null
    } finally {
      refreshing.value = false
    }
  }

  return {
    isConnected,
    institutionName,
    accountName,
    lastSyncedAt,
    lastManualRefreshAt,
    status,
    loading,
    refreshing,
    error,
    pendingAccounts,
    isSyncing,
    hasError,
    isAwaitingAccount,
    cooldownRemaining,
    cooldownSeconds,
    fetchStatus,
    enroll,
    confirmAccount,
    disconnect,
    doRefreshBalance,
  }
})

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
