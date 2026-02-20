import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types/auth'
import { fetchCurrentUser, logout as apiLogout } from '@/api/auth'
import { ApiError } from '@/api/client'
import { useCurrencyStore } from '@/stores/currency'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const checked = ref(false)
  const loading = ref(false)

  const isAuthenticated = computed(() => user.value !== null)

  async function checkAuth() {
    if (checked.value) return
    loading.value = true
    try {
      user.value = await fetchCurrentUser()
      const currency = useCurrencyStore()
      currency.initFromUser(
        user.value.account_currency ?? null,
        user.value.display_currency ?? null,
      )
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        user.value = null
      } else {
        throw err
      }
    } finally {
      checked.value = true
      loading.value = false
    }
  }

  async function logout() {
    await apiLogout()
    user.value = null
    // Keep checked = true so the router guard sees "not authenticated"
    // immediately instead of re-fetching /auth/me (which triggers a
    // competing 401 redirect that cancels the navigation).
    const currency = useCurrencyStore()
    currency.$reset()
  }

  return { user, checked, loading, isAuthenticated, checkAuth, logout }
})
