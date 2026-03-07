import { api } from './client'
import type { User } from '@/types/auth'

/** Fetch the currently authenticated user. Throws ApiError(401) if not logged in. */
export const fetchCurrentUser = () => api.get<User>('/auth/me')

/** Redirect to Discord OAuth2 login. */
export const loginRedirect = () => {
  window.location.href = '/api/auth/login'
}

/** Clear the session cookie. */
export const logout = () => api.post<void>('/auth/logout')

/** Mark a specific guided tour as completed for the current user. */
export const markTourComplete = (tourName: string) =>
  api.patch<void>(`/auth/me/tour-complete?tour_name=${encodeURIComponent(tourName)}`)

/** Clear all completed tours so the guided walkthrough replays on next visit. */
export const resetTours = () => api.post<void>('/auth/me/reset-tours')

/** Mark a specific modal as permanently dismissed for the current user. */
export const dismissModal = (modalKey: string) =>
  api.patch<void>(`/auth/me/dismiss-modal?modal_key=${encodeURIComponent(modalKey)}`)

/** Set the user's preferred UI language. */
export const setLanguage = (language: string) =>
  api.patch<void>(`/auth/me/language?language=${encodeURIComponent(language)}`)
