import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types/auth'
import { fetchCurrentUser, logout as apiLogout } from '@/api/auth'
import { ApiError } from '@/api/client'

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
  }

  return { user, checked, loading, isAuthenticated, checkAuth, logout }
})
