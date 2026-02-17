import { api } from './client'
import type { BalanceSnapshotResponse, ManualBalanceCreate, TransactionResponse } from '@/types/balance'

export const fetchCurrentBalance = () =>
  api.get<BalanceSnapshotResponse | null>('/balance/current')

export const fetchBalanceHistory = (limit = 100) =>
  api.get<BalanceSnapshotResponse[]>(`/balance/history?limit=${limit}`)

export const createManualBalance = (data: ManualBalanceCreate) =>
  api.post<BalanceSnapshotResponse>('/balance/manual', data)

export const fetchTransactions = () =>
  api.get<TransactionResponse[]>('/transactions')
