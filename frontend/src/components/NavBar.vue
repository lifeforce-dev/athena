<template>
  <nav class="nav">
    <div class="nav-brand">Athena</div>
    <div class="nav-tabs">
      <router-link
        v-for="tab in tabs"
        :key="tab.to"
        :to="tab.to"
        class="nt"
        active-class="active"
      >
        {{ tab.label }}
      </router-link>
    </div>
    <div class="nav-spacer" />
    <button
      class="nav-currency"
      :class="{ converted: currency.isConverted }"
      :disabled="currency.rateLoading"
      @click="currency.toggleDisplay()"
    >
      {{ currency.displayCurrency === 'USD' ? '$ USD' : '\u20A9 KRW' }}
    </button>
    <span v-if="auth.user" class="nav-user">{{ auth.user.username }}</span>
    <button class="nav-logout" @click="handleLogout">Logout</button>
  </nav>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCurrencyStore } from '@/stores/currency'

const auth = useAuthStore()
const currency = useCurrencyStore()
const router = useRouter()

const tabs = [
  { to: '/', label: 'Dashboard' },
  { to: '/commitments', label: 'Commitments' },
  { to: '/simulation', label: 'Simulation' },
]

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.nav {
  display: flex;
  align-items: center;
  backdrop-filter: blur(24px);
  background: var(--panel);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 10;
}

.nav-brand {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 11px;
  color: var(--bright);
  padding: 0 20px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.nav-tabs {
  display: flex;
  margin-left: 8px;
}

.nt {
  padding: 14px 18px;
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--dim);
  cursor: pointer;
  transition: color 0.2s;
  display: block;
  text-decoration: none;
}

.nt:hover {
  color: var(--text);
}

.nt.active {
  color: var(--bright);
}

.nt.active::after {
  content: '';
  display: block;
  width: 4px;
  height: 4px;
  margin: 4px auto 0;
  border-radius: 50%;
  background: var(--income);
}

.nav-spacer {
  flex: 1;
}

.nav-currency {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--dim);
  background: none;
  border: 1px solid transparent;
  padding: 6px 12px;
  margin-right: 4px;
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}

.nav-currency:hover {
  color: var(--text);
  border-color: var(--border);
}

.nav-currency.converted {
  color: var(--income);
  border-color: color-mix(in srgb, var(--income) 30%, transparent);
}

.nav-currency:disabled {
  opacity: 0.4;
  cursor: wait;
}

.nav-user {
  font-size: 11px;
  color: var(--dim);
  padding: 0 8px;
  white-space: nowrap;
}

.nav-logout {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--dim);
  background: none;
  border: none;
  padding: 14px 20px;
  cursor: pointer;
  transition: color 0.2s;
}

.nav-logout:hover {
  color: var(--danger);
}
</style>
