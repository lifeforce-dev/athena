import { api } from './client'

/** Check whether the backend has dev mode enabled. */
export const fetchDevStatus = () =>
  api.get<{ dev_mode: boolean }>('/dev/status')

/** Wipe all data for the current user (dev mode only). */
export const resetUser = () =>
  api.post<void>('/dev/reset-user')
