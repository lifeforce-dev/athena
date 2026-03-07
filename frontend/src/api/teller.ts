import { api } from './client'
import type {
  TellerEnrollRequest,
  TellerEnrollResponse,
  TellerNonceResponse,
  TellerSelectAccountRequest,
  TellerStatusResponse,
} from '@/types/teller'

export function getTellerNonce() {
  return api.get<TellerNonceResponse>('/teller/nonce')
}

export function enrollTeller(data: TellerEnrollRequest) {
  return api.post<TellerEnrollResponse>('/teller/enroll', data)
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
