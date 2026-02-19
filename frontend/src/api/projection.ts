import { api } from './client'
import type { ProjectionResponse } from '@/types/projection'

export async function fetchProjection(asOf: string, fromDate?: string): Promise<ProjectionResponse> {
  const params = new URLSearchParams({ as_of: asOf })
  if (fromDate) {
    params.set('from_date', fromDate)
  }
  return api.get<ProjectionResponse>(`/projection?${params.toString()}`)
}

export interface ScenarioRequest {
  as_of: string
  from_date?: string
  excluded_ids: number[]
  amount_overrides: Record<number, string>
}

export async function fetchScenarioProjection(body: ScenarioRequest): Promise<ProjectionResponse> {
  return api.post<ProjectionResponse>('/projection/scenario', body)
}
