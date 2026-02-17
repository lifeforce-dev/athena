import type { components } from '@/types/generated/api'

/** Current user profile returned by GET /api/auth/me. */
export type User = components['schemas']['UserResponse']
