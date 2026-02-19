import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { registerUnauthorizedHandler } from './api/client'
import { useAuthStore } from './stores/auth'
import './styles/base.css'
import './styles/utilities.css'
import './styles/tour.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Reset auth state and redirect to login on any 401 response.
const auth = useAuthStore()
registerUnauthorizedHandler(() => {
  auth.user = null
  router.push({ name: 'login' })
})

app.mount('#app')
