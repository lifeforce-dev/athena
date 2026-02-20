/**
 * Guided product tours using driver.js.
 *
 * Each major view (Dashboard, Commitments, Simulation) has its own
 * independent tour. Tours auto-trigger for real users on first login
 * (when tour_completed_at is null) and can be explicitly triggered
 * via the ?tour=<name> query parameter (used by demo flow).
 */
import { onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { driver, type DriveStep } from 'driver.js'
import 'driver.js/dist/driver.css'
import { useAuthStore } from '@/stores/auth'
import { markTourComplete } from '@/api/auth'

// ── Tour step definitions ──

const DASHBOARD_STEPS: DriveStep[] = [
  {
    element: '[data-tour="balance"]',
    popover: {
      title: 'Your Balance at a Glance',
      description: 'This is your real bank balance. Tap it anytime to update -- everything recalculates instantly.',
    },
  },
  {
    element: '[data-tour="gauge"]',
    popover: {
      title: 'Financial Health Shield',
      description: 'Green means you are cruising. Yellow means things are tight. Red means action needed. This gauge looks 90 days ahead so you are never surprised.',
    },
  },
  {
    element: '[data-tour="bills"]',
    popover: {
      title: 'Bills Coming Up',
      description: 'See exactly what is due this week and next. No more scrambling to remember which bills hit when.',
    },
  },
  {
    element: '[data-tour="trajectory"]',
    popover: {
      title: 'Your Cash Trajectory',
      description: 'A day-by-day map of your money for the next 90 days. Hover any point to see exactly what happens and when. The dips show you where to watch out.',
    },
  },
  {
    element: '[data-tour="cause-panel"]',
    popover: {
      title: 'What Is Eating Your Cash',
      description: 'This breaks down your tightest pay period. See which expenses hit hardest so you know where to cut if things get tight.',
    },
  },
  {
    element: '[data-tour="currency-toggle"]',
    popover: {
      title: 'Switch Currencies',
      description: 'Living abroad or just curious? Toggle between USD and KRW with live exchange rates. Every number in the app converts instantly.',
    },
  },
]

const COMMITMENTS_STEPS: DriveStep[] = [
  {
    element: '[data-tour="commitments-summary"]',
    popover: {
      title: 'Your Monthly Snapshot',
      description: 'Income vs. expenses at a glance. This is the heartbeat of your finances -- one look tells you if you are gaining or losing ground each month.',
    },
  },
  {
    element: '[data-tour="commitments-add"]',
    popover: {
      title: 'Add Anything',
      description: 'Rent, subscriptions, paychecks, one-time purchases -- add them all here. The more Athena knows, the more accurate your projections get.',
    },
  },
  {
    element: '[data-tour="commitments-group"]',
    popover: {
      title: 'Organized by Category',
      description: 'Your commitments are grouped automatically. Click any amount to edit it. Spot a subscription you forgot about? This is where it lives.',
    },
  },
]

const SIMULATION_STEPS: DriveStep[] = [
  {
    element: '[data-tour="sim-grid"]',
    popover: {
      title: 'What-If Playground',
      description: 'This is where Athena gets powerful. Toggle any bill on or off, adjust amounts, and instantly see how it changes your financial future.',
    },
  },
  {
    element: '[data-tour="sim-summary"]',
    popover: {
      title: 'Instant Impact',
      description: 'Every change you make updates this panel in real time. See your simulated net per month and hit Run to visualize the full trajectory.',
    },
  },
]

// ── Tour registry (name -> route -> steps) ──

const TOURS: Record<string, { route: string; steps: DriveStep[] }> = {
  dashboard: { route: '/', steps: DASHBOARD_STEPS },
  commitments: { route: '/commitments', steps: COMMITMENTS_STEPS },
  simulation: { route: '/simulation', steps: SIMULATION_STEPS },
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
 * 2. Auto: real user whose tour_completed_at is null visits a page
 *    that has a tour definition and hasn't been shown this session.
 */
export function useTour() {
  const route = useRoute()
  const router = useRouter()
  const auth = useAuthStore()

  onMounted(async () => {
    const explicitTour = route.query.tour as string | undefined
    const tourName = explicitTour ?? ROUTE_TO_TOUR[route.path]
    if (!tourName || !TOURS[tourName]) return

    // Skip if already shown this session.
    if (completedThisSession.has(tourName)) return

    // Auto-trigger only fires when the user hasn't completed onboarding.
    if (!explicitTour && auth.user?.tour_completed_at) return

    // Remove the query param so refreshing does not restart the tour.
    if (explicitTour) {
      router.replace({ query: {} })
    }

    // Wait for the view to finish rendering.
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 600))

    completedThisSession.add(tourName)

    runTour(TOURS[tourName].steps, async () => {
      // Persist completion server-side for real (non-demo) users.
      if (auth.user && !auth.user.tour_completed_at) {
        try {
          await markTourComplete()
          auth.user.tour_completed_at = new Date().toISOString()
        } catch {
          // Non-critical -- tour still ran, persistence failed silently.
        }
      }
    })
  })
}
