/** Teller integration types — matches backend Pydantic schemas. */

export type TellerStatusValue =
  | 'awaiting_account'
  | 'syncing'
  | 'active'
  | 'disconnected'
  | 'error'

/** POST /api/teller/enroll request body. */
export interface TellerEnrollRequest {
  access_token: string
  enrollment_id: string
  institution: string
  /** Ed25519 signatures from Teller Connect enrollment callback. */
  signatures: string[]
  /** Teller's user.id from the enrollment callback. */
  teller_user_id: string
  /** Server-generated nonce passed to Teller Connect. */
  nonce: string
  /** HMAC of the nonce for stateless server-side verification. */
  nonce_mac: string
}

/** POST /api/teller/select-account request body. */
export interface TellerSelectAccountRequest {
  account_id: string
}

/** A single bank account option returned during enrollment. */
export interface TellerAccountOption {
  id: string
  name: string
  type: string
  subtype: string
  currency: string
  institution_name: string
}

/** Response from POST /api/teller/enroll. */
export interface TellerEnrollResponse {
  status: TellerStatusValue
  institution_name: string
  accounts: TellerAccountOption[]
}

/** Response from GET /api/teller/status and POST /api/teller/select-account. */
export interface TellerStatusResponse {
  is_connected: boolean
  institution_name: string | null
  account_name: string | null
  last_synced_at: string | null
  last_manual_refresh_at: string | null
  status: TellerStatusValue
}

/** Response from POST /api/teller/refresh-balance. */
export interface RefreshBalanceResponse {
  balance: string
  cooldown_started_at: string
  cooldown_seconds: number
}

/** Response from GET /api/teller/nonce. */
export interface TellerNonceResponse {
  nonce: string
  nonce_mac: string
}
