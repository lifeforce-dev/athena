<template>
  <div class="app-root">
    <NavBar v-if="auth.isAuthenticated" />
    <router-view />
  </div>
</template>

<script setup lang="ts">
import NavBar from '@/components/NavBar.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<style scoped>
.app-root {
  min-height: 100vh;
}
</style>
