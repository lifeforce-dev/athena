import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { registerUnauthorizedHandler, registerDisplayCurrencyProvider } from './api/client'
import { useAuthStore } from './stores/auth'
import { useCurrencyStore } from './stores/currency'
import './styles/base.css'
import './styles/utilities.css'
import './styles/tour.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Reset all session state and redirect to login on any 401 response.
const auth = useAuthStore()
const currency = useCurrencyStore()
registerUnauthorizedHandler(() => {
  auth.user = null
  auth.checked = false
  currency.$reset()
  router.push({ name: 'login' })
})

// Every API request carries the display currency so the backend knows
// exactly what currency incoming amounts are denominated in.
registerDisplayCurrencyProvider(() => currency.displayCurrency)

app.mount('#app')
