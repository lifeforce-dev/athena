/**
 * Module-level flag that signals whether demo data should be loaded.
 *
 * Set to true by DemoView or App.vue before navigating to the dashboard.
 * Read by useDashboard to decide whether to fetch from /demo/dashboard.
 * Reset by useTour when the tour completes or is dismissed.
 *
 * Using a module-level ref avoids timing issues with async router
 * navigation and query-param reading during component setup.
 */
import { ref } from 'vue'

export const demoTourActive = ref(false)
