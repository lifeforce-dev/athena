<template>
  <button
    class="cd-btn"
    :class="{ 'on-cd': onCooldown, refreshing }"
    :disabled="onCooldown || refreshing"
    :title="tooltipText"
    @click.stop="$emit('refresh')"
  >
    <!-- Refresh icon (SVG arrow circle) -->
    <svg
      class="cd-icon"
      :class="{ spinning: refreshing }"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2.5"
      stroke-linecap="round"
      stroke-linejoin="round"
    >
      <polyline points="23 4 23 10 17 10" />
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
    </svg>

    <!--
      Radial cooldown overlay — a dark conic-gradient that
      shrinks clockwise from 12 o'clock as cooldown elapses, revealing
      the icon underneath.
    -->
    <div
      v-if="onCooldown"
      class="cd-sweep"
      :style="{ '--cd-angle': sweepAngle + 'deg' }"
    />
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '@/composables/useI18n'

const props = defineProps<{
  /** Seconds remaining on cooldown (from teller store, ticks down). */
  remaining: number
  /** Total cooldown duration in seconds. */
  total: number
  /** Whether a refresh API call is in flight. */
  refreshing: boolean
}>()

defineEmits<{
  refresh: []
}>()

const { t } = useI18n()

const onCooldown = computed(() => props.remaining > 0)

/** Degrees of dark overlay remaining (360 = just started, 0 = done). */
const sweepAngle = computed(() => {
  if (props.total <= 0) return 0
  return Math.round((props.remaining / props.total) * 360)
})

const tooltipText = computed(() => {
  if (props.refreshing) return t('hero.refresh_loading')
  if (!onCooldown.value) return t('hero.refresh_balance')
  const mins = Math.ceil(props.remaining / 60)
  return t('hero.refresh_cooldown', { minutes: mins })
})
</script>

<style scoped>
.cd-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 18px;
  padding: 0;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 0;
  background: transparent;
  color: var(--dim);
  cursor: pointer;
  overflow: hidden;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
  vertical-align: middle;
}

.cd-btn:hover:not(:disabled) {
  color: var(--safe);
  border-color: rgba(52, 211, 153, 0.4);
  background: rgba(52, 211, 153, 0.06);
}

.cd-btn:disabled {
  cursor: default;
  opacity: 1;
}

.cd-icon {
  width: 11px;
  height: 11px;
  position: relative;
  z-index: 2;
}

.cd-icon.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ── Radial sweep overlay ── */

.cd-sweep {
  position: absolute;
  inset: 0;
  z-index: 3;
  background: conic-gradient(
    from 0deg,
    transparent 0deg,
    transparent calc(360deg - var(--cd-angle)),
    rgba(0, 0, 0, 0.65) calc(360deg - var(--cd-angle)),
    rgba(0, 0, 0, 0.65) 360deg
  );
  pointer-events: none;
}

.on-cd .cd-icon {
  color: var(--muted);
}
</style>
