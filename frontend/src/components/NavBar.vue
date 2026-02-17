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
    <button class="nav-logout" @click="handleLogout">Logout</button>
  </nav>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
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
