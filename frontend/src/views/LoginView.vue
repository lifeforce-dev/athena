<template>
  <div class="login-page">
    <div class="login-frame">
      <div class="login-accent" />
      <div class="login-content">
        <div class="login-mark">
          <span class="login-brand">Athena</span>
          <span class="login-ver">v1</span>
        </div>
        <div class="login-rule" />
        <p class="login-desc">Cash flow projection<br />and financial awareness.</p>
        <button class="login-btn" @click="login">
          <span class="login-btn-label">Sign in with Discord</span>
          <span class="login-btn-arrow">&rarr;</span>
        </button>
        <div class="login-footer">
          <span class="login-foot-dot" />
          <span class="login-foot-text">Secure session via OAuth 2.0</span>
        </div>
      </div>
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
  background: var(--bg);
}

.login-frame {
  position: relative;
  background: var(--panel);
  border: 1px solid var(--border);
  max-width: 340px;
  width: 100%;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.5);
}

.login-accent {
  height: 2px;
  background: linear-gradient(
    90deg,
    var(--income) 0%,
    rgba(167, 139, 250, 0.3) 60%,
    transparent 100%
  );
}

.login-content {
  padding: 36px 32px 28px;
}

.login-mark {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.login-brand {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 22px;
  color: var(--bright);
  letter-spacing: 0.08em;
}

.login-ver {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--dim);
  letter-spacing: 0.05em;
}

.login-rule {
  width: 28px;
  height: 1px;
  background: var(--border);
  margin: 14px 0 16px;
}

.login-desc {
  font-size: 12px;
  line-height: 1.6;
  color: var(--dim);
  margin-bottom: 28px;
}

.login-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 16px;
  background: transparent;
  border: 1px solid rgba(167, 139, 250, 0.2);
  color: var(--income);
  cursor: pointer;
  transition: all 0.15s;
}

.login-btn:hover {
  background: rgba(167, 139, 250, 0.08);
  border-color: rgba(167, 139, 250, 0.35);
}

.login-btn:active {
  background: rgba(167, 139, 250, 0.12);
}

.login-btn-label {
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.login-btn-arrow {
  font-size: 14px;
  opacity: 0.5;
  transition: opacity 0.15s, transform 0.15s;
}

.login-btn:hover .login-btn-arrow {
  opacity: 1;
  transform: translateX(2px);
}

.login-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.login-foot-dot {
  width: 4px;
  height: 4px;
  background: var(--safe);
  flex-shrink: 0;
}

.login-foot-text {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--dim);
  letter-spacing: 0.04em;
}
</style>
