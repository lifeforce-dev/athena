import { api } from './client'
import type { ProjectionResponse } from '@/types/projection'
import type { CommitmentResponse } from '@/types/commitment'

export function fetchDemoProjection(): Promise<ProjectionResponse> {
  return api.get<ProjectionResponse>('/demo/dashboard')
}

export function fetchDemoCommitments(): Promise<CommitmentResponse[]> {
  return api.get<CommitmentResponse[]>('/demo/commitments')
}

export function fetchDemoSimulation(): Promise<ProjectionResponse> {
  return api.get<ProjectionResponse>('/demo/simulation')
}
