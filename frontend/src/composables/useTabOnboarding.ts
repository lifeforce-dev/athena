/**
 * Declarative tab onboarding system.
 *
 * Each view declares an OnboardingConfig and calls useTabOnboarding().
 * The composable handles:
 *   - driver.js tooltip tour
 *   - Tour completion persistence
 *   - FTE auto-advance (enable next tab glow after tour ends)
 *   - Non-dismissable tooltips during FTE
 *
 * Adding onboarding to a new tab = one config object + one composable call.
 */
import { onMounted, nextTick } from 'vue'
import { driver, type DriveStep, type Driver } from 'driver.js'
import 'driver.js/dist/driver.css'
import { useAuthStore } from '@/stores/auth'
import { markTourComplete } from '@/api/auth'
import { useI18n } from '@/composables/useI18n'
import { demoTourActive } from '@/stores/demoTour'
import {
  fteActive,
  fteShowCompletionDialog,
  fteBetweenTours,
  advanceFte,
} from '@/stores/fte'

// ── Types ──

type TFn = (key: string, params?: Record<string, string | number>) => string

export interface OnboardingConfig {
  /** Unique tour name, matches completed_tours on the user profile. */
  name: string
  /** Driver.js step definitions for this tab's tour. */
  steps: (t: TFn) => DriveStep[]
}

const RENDER_WAIT_MS = 600

/** Tracks which tours have already run this SPA session to avoid repeats. */
const completedThisSession = new Set<string>()

/** Clear the session-level tour cache (used by dev reset). */
export function resetTourSessionCache() {
  completedThisSession.clear()
}

/**
 * Active driver.js instance so skip-tour can destroy it mid-run.
 * Exported for NavBar's skip button.
 */
export let activeDriver: Driver | null = null

// ── Tour runner ──

function runTour(steps: DriveStep[], allowClose: boolean): Promise<void> {
  return new Promise((resolve) => {
    activeDriver = driver({
      showProgress: true,
      animate: true,
      overlayColor: 'rgba(0, 0, 0, 0.7)',
      stagePadding: 8,
      stageRadius: 4,
      popoverClass: 'athena-tour-popover',
      allowClose,
      steps,
      onDestroyed: () => {
        activeDriver = null
        resolve()
      },
    })
    activeDriver.drive()
  })
}

// ── Helpers ──

function shouldRun(name: string, auth: ReturnType<typeof useAuthStore>): boolean {
  if (completedThisSession.has(name)) return false

  // FTE flow always runs regardless of server-side completion.
  if (demoTourActive.value) return true

  const completed = auth.user?.completed_tours ?? []
  return !completed.includes(name)
}

async function persistCompletion(name: string, auth: ReturnType<typeof useAuthStore>) {
  completedThisSession.add(name)

  if (!auth.user) return
  const completed = auth.user.completed_tours ?? []
  if (completed.includes(name)) return

  try {
    await markTourComplete(name)
    auth.user.completed_tours = [...completed, name]
  } catch {
    // Non-critical.
  }
}

// ── Main composable ──

export function useTabOnboarding(config: OnboardingConfig) {
  const auth = useAuthStore()
  const { t } = useI18n()

  onMounted(async () => {
    if (!shouldRun(config.name, auth)) return

    await nextTick()
    // Wait for the view to render its DOM so data-tour elements exist.
    await new Promise((resolve) => setTimeout(resolve, RENDER_WAIT_MS))

    // Remove the cover div if it exists (from CurrencyPrompt).
    document.getElementById('demo-tour-cover')?.remove()

    // Clear between-tours overlay when a new tour starts.
    fteBetweenTours.value = false

    const steps = config.steps(t)

    // During FTE: tooltips are non-dismissable (no X, no overlay click).
    const allowClose = !fteActive.value
    await runTour(steps, allowClose)

    // Persist completion.
    await persistCompletion(config.name, auth)

    // FTE: enable next tab glow, or show completion dialog.
    if (fteActive.value) {
      const next = advanceFte()
      if (next === 'done') {
        fteShowCompletionDialog.value = true
      } else {
        // Next tab is now glowing. Dim page so it stands out.
        fteBetweenTours.value = true
      }
    }
  })
}
