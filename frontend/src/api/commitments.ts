import { api } from './client'
import type { CommitmentResponse, CommitmentCreate, CommitmentUpdate } from '@/types/commitment'

export const fetchCommitments = () =>
  api.get<CommitmentResponse[]>('/commitments')

export const createCommitment = (data: CommitmentCreate) =>
  api.post<CommitmentResponse>('/commitments', data)

export const updateCommitment = (id: number, data: CommitmentUpdate) =>
  api.put<CommitmentResponse>(`/commitments/${id}`, data)

export const deleteCommitment = (id: number) =>
  api.del(`/commitments/${id}`)
