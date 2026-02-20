<template>
  <div class="demo-page">
    <div class="demo-frame">
      <div class="demo-accent" />
      <div class="demo-content">
        <div class="demo-mark">
          <span class="demo-brand">Athena</span>
          <span class="demo-ver">demo</span>
        </div>
        <div class="demo-rule" />
        <p v-if="error" class="demo-error">{{ error }}</p>
        <p v-else class="demo-desc">Setting up your demo environment...</p>
        <div class="demo-dots"><span /><span /><span /></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/api/client'

const router = useRouter()
const auth = useAuthStore()
const error = ref('')

onMounted(async () => {
  try {
    await api.post('/auth/demo-start')

    // Force auth store to re-check (clear cached state).
    auth.checked = false
    await auth.checkAuth()

    router.replace({ name: 'dashboard', query: { tour: 'dashboard' } })
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Failed to start demo'
  }
})
</script>

<style scoped>
.demo-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
}

.demo-frame {
  position: relative;
  background: var(--panel);
  border: 1px solid var(--border);
  max-width: 340px;
  width: 100%;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.5);
}

.demo-accent {
  height: 2px;
  background: linear-gradient(
    90deg,
    var(--safe) 0%,
    rgba(52, 211, 153, 0.3) 60%,
    transparent 100%
  );
}

.demo-content {
  padding: 36px 32px 28px;
  text-align: center;
}

.demo-mark {
  display: flex;
  align-items: baseline;
  gap: 8px;
  justify-content: center;
}

.demo-brand {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 22px;
  color: var(--bright);
  letter-spacing: 0.08em;
}

.demo-ver {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--safe);
  letter-spacing: 0.05em;
}

.demo-rule {
  width: 28px;
  height: 1px;
  background: var(--border);
  margin: 14px auto 16px;
}

.demo-desc {
  font-size: 12px;
  line-height: 1.6;
  color: var(--dim);
}

.demo-error {
  font-size: 12px;
  line-height: 1.6;
  color: var(--danger);
}

.demo-dots {
  display: flex;
  gap: 6px;
  justify-content: center;
  margin-top: 20px;
}

.demo-dots span {
  width: 4px;
  height: 4px;
  background: var(--dim);
  animation: pulse 1.2s ease-in-out infinite;
}

.demo-dots span:nth-child(2) { animation-delay: 0.2s; }
.demo-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes pulse {
  0%, 100% { opacity: 0.2; }
  50% { opacity: 1; }
}
</style>
