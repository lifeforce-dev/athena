<template>
  <div class="app-root">
    <template v-if="needsCurrencyPrompt">
      <CurrencyPrompt @done="onCurrencySet" />
    </template>
    <template v-else>
      <NavBar v-if="auth.isAuthenticated" />
      <router-view />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import NavBar from '@/components/NavBar.vue'
import CurrencyPrompt from '@/components/CurrencyPrompt.vue'
import { useAuthStore } from '@/stores/auth'
import { useCurrencyStore } from '@/stores/currency'

const auth = useAuthStore()
const currency = useCurrencyStore()

/**
 * True when the user is logged in, auth check is done, but
 * they haven't set their account currency yet.
 */
const needsCurrencyPrompt = computed(
  () => auth.checked && auth.isAuthenticated && !currency.accountCurrencySet,
)

function onCurrencySet() {
  // Prompt dismissed -- store already updated, reactivity handles the rest.
}
</script>

<style scoped>
.app-root {
  min-height: 100vh;
}
</style>
