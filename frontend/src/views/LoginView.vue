<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">Athena</div>
      <p class="login-tagline">Cash flow projection and financial awareness.</p>
      <button class="login-btn" @click="login">
        Sign in with Discord
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { loginRedirect } from '@/api/auth'

function login() {
  loginRedirect()
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-card {
  backdrop-filter: blur(24px);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  padding: 48px 40px;
  text-align: center;
  max-width: 380px;
  width: 100%;
  box-shadow: var(--shadow-modal);
}

.login-brand {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 28px;
  color: var(--bright);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.login-tagline {
  font-size: 12px;
  color: var(--dim);
  margin-bottom: 32px;
}

.login-btn {
  width: 100%;
  padding: 12px 24px;
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid rgba(167, 139, 250, 0.2);
  background: rgba(167, 139, 250, 0.15);
  color: var(--income);
  transition: all 0.15s;
}

.login-btn:hover {
  background: rgba(167, 139, 250, 0.25);
}
</style>
