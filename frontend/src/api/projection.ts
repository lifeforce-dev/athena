import { api } from './client'
import type { ProjectionResponse } from '@/types/projection'

export async function fetchProjection(asOf: string, fromDate?: string): Promise<ProjectionResponse> {
  const params = new URLSearchParams({ as_of: asOf })
  if (fromDate) {
    params.set('from_date', fromDate)
  }
  return api.get<ProjectionResponse>(`/projection?${params.toString()}`)
}
