import type { components } from '@/types/generated/api'

export type CommitmentResponse = components['schemas']['CommitmentResponse']
export type CommitmentCreate = components['schemas']['CommitmentCreate']
export type CommitmentUpdate = components['schemas']['CommitmentUpdate']
export type Frequency = CommitmentCreate['frequency']
