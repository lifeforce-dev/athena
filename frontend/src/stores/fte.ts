/**
 * First-Time Experience (FTE) state machine.
 *
 * Tracks which step of the progressive onboarding the user is on.
 * NavBar reads this to lock/glow tabs. useTabOnboarding reads it
 * to decide whether to auto-advance after a tour finishes.
 */
import { ref, computed } from 'vue'
import type { useAuthStore } from './auth'

export const FTE_STEPS = ['dashboard', 'commitments', 'simulation'] as const
export type FteStep = (typeof FTE_STEPS)[number]

export const FTE_ROUTES: Record<FteStep, string> = {
  dashboard: '/',
  commitments: '/commitments',
  simulation: '/simulation',
}

/** True while the user is inside the FTE flow. */
export const fteActive = ref(false)

/** Index into FTE_STEPS -- how far the user has progressed. */
export const fteStepIndex = ref(0)

/**
 * True once the user has clicked a glowing tab to begin the first tour.
 * While false, the FTE welcome screen shows instead of the dashboard.
 */
export const fteStarted = ref(false)

/** Show the completion dialog after the last tour finishes. */
export const fteShowCompletionDialog = ref(false)

/**
 * True between tours -- user finished one tour, next tab glows, waiting for click.
 * Used to dim the page content so the glowing tab stands out.
 */
export const fteBetweenTours = ref(false)

export const currentStep = computed(() => FTE_STEPS[fteStepIndex.value])

/** True if the given tab should be accessible during FTE. */
export function isTabUnlocked(tabName: string): boolean {
  if (!fteActive.value) return true
  const idx = FTE_STEPS.indexOf(tabName as FteStep)
  if (idx === -1) return true
  return idx <= fteStepIndex.value
}

/** True if the given tab is the next one that should pulse/glow. */
export function isTabGlowing(tabName: string): boolean {
  if (!fteActive.value) return false
  const idx = FTE_STEPS.indexOf(tabName as FteStep)
  return idx === fteStepIndex.value
}

/** Advance to the next FTE step after a tour completes. Returns the new step or 'done'. */
export function advanceFte(): FteStep | 'done' {
  if (fteStepIndex.value < FTE_STEPS.length - 1) {
    fteStepIndex.value++
    return FTE_STEPS[fteStepIndex.value]
  }
  return 'done'
}

/** End the FTE completely (skip or natural completion). */
export function endFte() {
  fteActive.value = false
  fteStarted.value = false
  fteStepIndex.value = 0
  fteShowCompletionDialog.value = false
  fteBetweenTours.value = false
}

/** Initialize FTE on login -- check which tours remain. */
export function initFte(auth: ReturnType<typeof useAuthStore>) {
  const completed = auth.user?.completed_tours ?? []
  const allDone = FTE_STEPS.every((step) => completed.includes(step))

  if (allDone) {
    fteActive.value = false
    return
  }

  const firstIncomplete = FTE_STEPS.findIndex((step) => !completed.includes(step))
  fteStepIndex.value = firstIncomplete >= 0 ? firstIncomplete : 0

  // Returning users who already completed some tours skip the welcome screen.
  fteStarted.value = fteStepIndex.value > 0
  fteActive.value = true
}
