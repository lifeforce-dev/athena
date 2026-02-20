<template>
  <div class="app-root">
    <NavBar v-if="auth.isAuthenticated" />
    <CurrencyPrompt
      v-if="auth.isAuthenticated && !currency.accountCurrencySet"
      @done="onCurrencySet"
    />
    <router-view />
  </div>
</template>

<script setup lang="ts">
import NavBar from '@/components/NavBar.vue'
import CurrencyPrompt from '@/components/CurrencyPrompt.vue'
import { useAuthStore } from '@/stores/auth'
import { useCurrencyStore } from '@/stores/currency'

const auth = useAuthStore()
const currency = useCurrencyStore()

function onCurrencySet() {
  // Prompt dismissed -- store is already updated.
}
</script>

<style scoped>
.app-root {
  min-height: 100vh;
}
</style>
