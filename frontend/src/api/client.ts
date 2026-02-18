export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

const API_BASE = '/api'

// Registered by the app after Pinia is ready (avoids circular imports).
let onUnauthorized: (() => void) | null = null
export function registerUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {}
  if (options?.body != null) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(`${API_BASE}${path}`, {
    headers,
    credentials: 'include',
    ...options,
  })

  if (!response.ok) {
    let message = response.statusText
    try {
      const body = await response.json()
      if (body?.detail) {
        message = body.detail
      }
    } catch {
      // Response wasn't JSON; fall back to statusText.
    }

    if (response.status === 401) {
      onUnauthorized?.()
    }

    throw new ApiError(response.status, message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'POST', body: data != null ? JSON.stringify(data) : undefined }),
  put: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: 'PUT', body: data != null ? JSON.stringify(data) : undefined }),
  del: (path: string) => request<void>(path, { method: 'DELETE' }),
}
