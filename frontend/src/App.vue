<template>
  <div class="app-root">
    <template v-if="needsCurrencyPrompt">
      <CurrencyPrompt @done="onCurrencySet" />
    </template>
    <template v-else>
      <NavBar v-if="auth.isAuthenticated" />
      <FteWelcome v-if="showFteWelcome" />
      <router-view v-else />
      <FteCompletionDialog v-if="fteShowCompletionDialog" />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import NavBar from '@/components/NavBar.vue'
import CurrencyPrompt from '@/components/CurrencyPrompt.vue'
import FteWelcome from '@/components/FteWelcome.vue'
import FteCompletionDialog from '@/components/FteCompletionDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useCurrencyStore } from '@/stores/currency'
import { demoTourActive } from '@/stores/demoTour'
import { fteActive, fteStarted, fteShowCompletionDialog, initFte } from '@/stores/fte'

const router = useRouter()
const auth = useAuthStore()
const currency = useCurrencyStore()

/**
 * True when the user is logged in, auth check is done, but
 * they haven't set their account currency yet.
 */
const needsCurrencyPrompt = computed(
  () => auth.checked && auth.isAuthenticated && !currency.accountCurrencySet,
)

/** Show the welcome screen when FTE is active but user hasn't clicked a tab yet. */
const showFteWelcome = computed(
  () => fteActive.value && !fteStarted.value,
)

// Initialize FTE for returning users who already set currency but
// haven't finished all tours. Runs once when auth check completes.
watch(
  () => auth.checked && auth.isAuthenticated && currency.accountCurrencySet,
  (ready) => {
    if (!ready) return
    // Only init if FTE isn't already active (avoid double-init after CurrencyPrompt).
    if (!fteActive.value) {
      initFte(auth)
      if (fteActive.value) {
        demoTourActive.value = true
      }
    }
  },
  { immediate: true },
)

function onCurrencySet() {
  // demoTourActive is already set by CurrencyPrompt before the save.
  initFte(auth)
  demoTourActive.value = true
  router.replace({ path: '/' })
}
</script>

<style scoped>
.app-root {
  min-height: 100vh;
}
</style>
