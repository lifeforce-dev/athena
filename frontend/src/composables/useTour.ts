/**
 * Guided product tour using driver.js.
 *
 * Triggered when ?tour=1 is in the URL (set by the /demo flow).
 * Walks the user through the key dashboard features with a sequence
 * of highlight popover steps.
 */
import { onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'

const TOUR_STEPS = [
  {
    element: '[data-tour="balance"]',
    popover: {
      title: 'Current Balance',
      description: 'Your real bank balance, pulled from your latest snapshot. Click to update it manually.',
    },
  },
  {
    element: '[data-tour="gauge"]',
    popover: {
      title: 'Shield Gauge',
      description: 'Shows how financially comfortable you are across the projection window. Green = safe, yellow = tight, red = danger.',
    },
  },
  {
    element: '[data-tour="trajectory"]',
    popover: {
      title: 'Cash Trajectory',
      description: 'A day-by-day projection of your balance. Hover over points to see what bills hit that day.',
    },
  },
  {
    element: '[data-tour="cause-panel"]',
    popover: {
      title: 'Expense Breakdown',
      description: 'Your tightest spending window. Shows which expenses contribute most to your lowest point.',
    },
  },
  {
    element: '[data-tour="bills"]',
    popover: {
      title: 'Bills This Week',
      description: 'Upcoming bills due in the next 7 days so you are never caught off guard.',
    },
  },
  {
    popover: {
      title: 'Explore More',
      description: 'Check out the Commitments tab to manage your bills, or the Simulation tab to run what-if scenarios. Enjoy!',
    },
  },
]

export function useTour() {
  const route = useRoute()
  const router = useRouter()

  onMounted(async () => {
    if (route.query.tour !== '1') return

    // Remove the query param so refreshing does not restart the tour.
    router.replace({ query: {} })

    // Wait for the dashboard to finish rendering.
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 600))

    const tourDriver = driver({
      showProgress: true,
      animate: true,
      overlayColor: 'rgba(0, 0, 0, 0.7)',
      stagePadding: 8,
      stageRadius: 4,
      popoverClass: 'athena-tour-popover',
      steps: TOUR_STEPS,
    })

    tourDriver.drive()
  })
}
