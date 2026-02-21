/**
 * Guided product tours using driver.js.
 *
 * Each major view (Dashboard, Commitments, Simulation) has its own
 * independent tour. Tours auto-trigger for real users who haven't
 * completed the specific page tour yet (tracked per-tour via the
 * completed_tours array on the user). Can also be explicitly triggered
 * via the ?tour=<name> query parameter (used by demo flow).
 */
import { onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { driver, type DriveStep } from 'driver.js'
import 'driver.js/dist/driver.css'
import { useAuthStore } from '@/stores/auth'
import { markTourComplete } from '@/api/auth'
import { useI18n } from '@/composables/useI18n'

// ── Tour step builders (resolved at runtime for i18n) ──

type T = (key: string, params?: Record<string, string | number>) => string

function dashboardSteps(t: T): DriveStep[] {
  return [
    { element: '[data-tour="balance"]', popover: { title: t('tour.balance_title'), description: t('tour.balance_desc') } },
    { element: '[data-tour="gauge"]', popover: { title: t('tour.gauge_title'), description: t('tour.gauge_desc') } },
    { element: '[data-tour="bills"]', popover: { title: t('tour.bills_title'), description: t('tour.bills_desc') } },
    { element: '[data-tour="trajectory"]', popover: { title: t('tour.trajectory_title'), description: t('tour.trajectory_desc') } },
    { element: '[data-tour="cause-panel"]', popover: { title: t('tour.cause_title'), description: t('tour.cause_desc') } },
    { element: '[data-tour="currency-toggle"]', popover: { title: t('tour.currency_title'), description: t('tour.currency_desc') } },
  ]
}

function commitmentsSteps(t: T): DriveStep[] {
  return [
    { element: '[data-tour="commitments-summary"]', popover: { title: t('tour.snapshot_title'), description: t('tour.snapshot_desc') } },
    { element: '[data-tour="commitments-add"]', popover: { title: t('tour.add_title'), description: t('tour.add_desc') } },
    { element: '[data-tour="commitments-group"]', popover: { title: t('tour.organized_title'), description: t('tour.organized_desc') } },
  ]
}

function simulationSteps(t: T): DriveStep[] {
  return [
    { element: '[data-tour="sim-grid"]', popover: { title: t('tour.whatif_title'), description: t('tour.whatif_desc') } },
    { element: '[data-tour="sim-summary"]', popover: { title: t('tour.impact_title'), description: t('tour.impact_desc') } },
  ]
}

// ── Tour registry (name -> route -> step builder) ──

const TOURS: Record<string, { route: string; steps: (t: T) => DriveStep[] }> = {
  dashboard: { route: '/', steps: dashboardSteps },
  commitments: { route: '/commitments', steps: commitmentsSteps },
  simulation: { route: '/simulation', steps: simulationSteps },
}

/** Reverse lookup: route path -> tour name. */
const ROUTE_TO_TOUR: Record<string, string> = Object.fromEntries(
  Object.entries(TOURS).map(([name, { route }]) => [route, name]),
)

/** Tracks which tours have already run this SPA session to avoid repeats. */
const completedThisSession = new Set<string>()

function runTour(steps: DriveStep[], onComplete?: () => void) {
  const tourDriver = driver({
    showProgress: true,
    animate: true,
    overlayColor: 'rgba(0, 0, 0, 0.7)',
    stagePadding: 8,
    stageRadius: 4,
    popoverClass: 'athena-tour-popover',
    steps,
    onDestroyed: () => onComplete?.(),
  })

  tourDriver.drive()
}

/**
 * Activate guided tours for the current view.
 *
 * Trigger modes:
 * 1. Explicit: ?tour=<name> query param (used by demo flow).
 * 2. Auto: real user who hasn't completed this specific tour yet
 *    visits a page that has a tour definition.
 */
export function useTour() {
  const route = useRoute()
  const router = useRouter()
  const auth = useAuthStore()
  const { t } = useI18n()

  onMounted(async () => {
    const explicitTour = route.query.tour as string | undefined
    const tourName = explicitTour ?? ROUTE_TO_TOUR[route.path]
    if (!tourName || !TOURS[tourName]) return

    // Skip if already shown this session.
    if (completedThisSession.has(tourName)) return

    // Auto-trigger only fires when the user hasn't completed this specific tour.
    const completed = auth.user?.completed_tours ?? []
    if (!explicitTour && completed.includes(tourName)) return

    // Remove the query param so refreshing does not restart the tour.
    if (explicitTour) {
      router.replace({ query: {} })
    }

    // Wait for the view to finish rendering.
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 600))

    completedThisSession.add(tourName)

    runTour(TOURS[tourName].steps(t), async () => {
      // Persist completion server-side for real (non-demo) users.
      if (auth.user && !completed.includes(tourName)) {
        try {
          await markTourComplete(tourName)
          auth.user.completed_tours = [...completed, tourName]
        } catch {
          // Non-critical -- tour still ran, persistence failed silently.
        }
      }
    })
  })
}
