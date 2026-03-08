import { api } from './client'
import type {
  TellerEnrollRequest,
  TellerEnrollResponse,
  TellerNonceResponse,
  TellerSelectAccountRequest,
  TellerStatusResponse,
  RefreshBalanceResponse,
} from '@/types/teller'

export function getTellerNonce() {
  return api.get<TellerNonceResponse>('/teller/nonce')
}

export function enrollTeller(data: TellerEnrollRequest) {
  return api.post<TellerEnrollResponse>('/teller/enroll', data)
}

export function getTellerAccounts() {
  return api.get<TellerEnrollResponse>('/teller/accounts')
}

export function selectTellerAccount(data: TellerSelectAccountRequest) {
  return api.post<TellerStatusResponse>('/teller/select-account', data)
}

export function getTellerStatus() {
  return api.get<TellerStatusResponse>('/teller/status')
}

export function disconnectTeller() {
  return api.del('/teller/disconnect')
}

export function refreshBalance() {
  return api.post<RefreshBalanceResponse>('/teller/refresh-balance', {})
}
