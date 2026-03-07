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
  status: TellerStatusValue
}
