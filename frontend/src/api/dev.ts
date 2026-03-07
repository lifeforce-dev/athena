import { api, ApiError } from './client'

/** Cached dev-mode status (null = not checked yet). */
let cachedDevMode: boolean | null = null

/** Check whether the backend has dev mode enabled.
 *  Caches the result so a 404 in production only fires once per session. */
export async function fetchDevStatus(): Promise<{ dev_mode: boolean }> {
  if (cachedDevMode !== null) return { dev_mode: cachedDevMode }

  try {
    const result = await api.get<{ dev_mode: boolean }>('/dev/status')
    cachedDevMode = result.dev_mode
    return result
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      cachedDevMode = false
    }
    throw err
  }
}

/** Wipe all data for the current user (dev mode only). */
export const resetUser = () =>
  api.post<void>('/dev/reset-user')
