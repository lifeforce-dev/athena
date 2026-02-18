<template>
  <section class="hero" :class="statusClass">
    <div class="hero-glass" :class="{ danger: statusClass === 'danger' }">
      <div class="hero-days">{{ daysCovered }}</div>
      <div class="hero-label">Day Projection</div>
      <div class="hero-verdict" :class="statusClass">{{ verdict }}</div>
    </div>

    <div class="hero-strip">
      <div class="hs-card hs-editable" @click="startEdit">
        <template v-if="!editing">
          <div class="hs-val" :style="{ color: 'var(--bright)' }">{{ formatDollars(currentBalance) }}</div>
          <div class="hs-lbl">Current <span class="hs-edit-hint">click to update</span></div>
        </template>
        <template v-else>
          <input
            ref="inputRef"
            v-model="editValue"
            class="hs-input"
            type="text"
            inputmode="decimal"
            placeholder="0"
            @keydown.enter="saveBalance"
            @keydown.escape="cancelEdit"
            @blur="cancelEdit"
          />
          <div class="hs-lbl">
            <button class="hs-save" @mousedown.prevent="saveBalance">Save</button>
            <span class="hs-cancel" @mousedown.prevent="cancelEdit">Esc</span>
          </div>
        </template>
      </div>
      <div class="hs-card hs-readonly">
        <div class="hs-val" :style="{ color: endColor }">{{ formatDollars(endBalance) }}</div>
        <div class="hs-lbl">After Window</div>
      </div>
      <div class="hs-card hs-readonly">
        <div class="hs-val" :style="{ color: 'var(--danger)' }">{{ formatDollars(lowestBalance) }}</div>
        <div class="hs-sub">{{ lowestDate }}</div>
        <div class="hs-lbl">Lowest Point</div>
      </div>
      <div class="hs-card hs-readonly">
        <div class="hs-val" :style="{ color: netColor }">{{ netLabel }}</div>
        <div class="hs-lbl">Net Change</div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { parseLocalDate, formatDollars } from '@/utils/format'

const props = defineProps<{
  currentBalance: number
  endBalance: number
  netChange: number
  lowestBalance: number
  lowestDate: string
  daysCovered: number
}>()

const emit = defineEmits<{
  updateBalance: [balance: number]
}>()

const editing = ref(false)
const editValue = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

function startEdit() {
  if (editing.value) return
  editing.value = true
  editValue.value = Math.round(props.currentBalance).toString()
  nextTick(() => {
    inputRef.value?.focus()
    inputRef.value?.select()
  })
}

function cancelEdit() {
  editing.value = false
}

function saveBalance() {
  const raw = editValue.value.replace(/[,$\s]/g, '')
  const num = parseFloat(raw)
  if (isNaN(num) || num < 0) return
  editing.value = false
  emit('updateBalance', num)
}

const statusClass = computed(() => {
  if (props.lowestBalance < 0) return 'danger'
  if (props.lowestBalance < 3000) return 'tight'
  return 'safe'
})

const verdict = computed(() => {
  if (statusClass.value === 'danger') return 'Critical'
  if (statusClass.value === 'tight') return 'Tight'
  return 'Comfortable'
})

const endColor = computed(() =>
  props.endBalance >= props.currentBalance ? 'var(--safe)' : 'var(--danger)'
)

const netColor = computed(() =>
  props.netChange >= 0 ? 'var(--safe)' : 'var(--danger)'
)

const netLabel = computed(() => {
  const sign = props.netChange >= 0 ? '+' : '-'
  return `${sign}${formatDollars(props.netChange)}`
})

const lowestDate = computed(() => {
  if (!props.lowestDate) return ''
  return parseLocalDate(props.lowestDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
})
</script>

<style scoped>
.hero {
  padding: 48px 32px 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  overflow: hidden;
}

.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.hero.safe::before {
  background: radial-gradient(ellipse 40% 50% at 50% 0%, var(--safe-glow), transparent);
}

.hero.tight::before {
  background: radial-gradient(ellipse 40% 50% at 50% 0%, var(--tight-glow), transparent);
}

.hero.danger::before {
  background: radial-gradient(ellipse 40% 50% at 50% 0%, var(--danger-glow), transparent);
}

.hero-glass {
  position: relative;
  z-index: 1;
  backdrop-filter: blur(16px);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  padding: 28px 40px 24px;
  text-align: center;
  max-width: 380px;
  width: 100%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.hero-glass.danger {
  border-color: rgba(248, 113, 113, 0.15);
  box-shadow: 0 0 0 1px rgba(248, 113, 113, 0.05), 0 0 40px rgba(248, 113, 113, 0.08);
}

.hero-days {
  font-family: var(--font-mono);
  font-size: 80px;
  font-weight: 700;
  line-height: 0.85;
  color: var(--bright);
}

.hero-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.25em;
  margin-top: 8px;
}

.hero-verdict {
  font-size: 18px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: 18px;
}

.hero-verdict.safe { color: var(--safe); }
.hero-verdict.tight { color: var(--tight); }
.hero-verdict.danger { color: var(--danger); }

.hero-strip {
  display: flex;
  gap: 28px;
  margin-top: 24px;
  position: relative;
  z-index: 1;
}

.hs-card {
  backdrop-filter: blur(16px);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px 18px;
  text-align: center;
  min-width: 120px;
  box-shadow: var(--shadow-sm);
}

.hs-editable {
  cursor: pointer;
  border-color: rgba(232, 236, 242, 0.12);
  transition: border-color 0.15s, background 0.15s;
}

.hs-editable:hover {
  border-color: rgba(232, 236, 242, 0.25);
  background: rgba(22, 26, 35, 0.95);
}

.hs-readonly {
  opacity: 0.55;
  border-style: dashed;
}

.hs-edit-hint {
  font-size: 7px;
  color: var(--muted);
  letter-spacing: 0;
  text-transform: none;
  font-weight: 400;
  margin-left: 4px;
}

.hs-input {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
  color: var(--bright);
  background: transparent;
  border: none;
  border-bottom: 1px solid rgba(232, 236, 242, 0.2);
  text-align: center;
  width: 100%;
  outline: none;
  padding: 0 0 4px;
}

.hs-input::placeholder {
  color: var(--muted);
}

.hs-save {
  background: none;
  border: 1px solid rgba(52, 211, 153, 0.25);
  color: var(--safe);
  font-size: 8px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 2px 8px;
  cursor: pointer;
  font-family: var(--font-sans);
}

.hs-save:hover {
  background: rgba(52, 211, 153, 0.08);
}

.hs-cancel {
  font-size: 7px;
  color: var(--muted);
  margin-left: 6px;
  cursor: pointer;
}

.hs-val {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
}

.hs-sub {
  font-size: 8px;
  color: var(--muted);
  font-family: var(--font-mono);
  margin-top: 1px;
}

.hs-lbl {
  font-size: 8px;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-top: 3px;
  font-weight: 700;
}

@media (max-width: 700px) {
  .hero-days { font-size: 56px; }
  .hero-strip { gap: 10px; flex-wrap: wrap; }
  .hs-card { min-width: 80px; padding: 10px 12px; }
}
</style>
