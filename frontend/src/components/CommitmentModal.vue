<template>
  <Teleport to="body">
    <div class="modal-overlay" :class="{ show: visible }" @click.self="emit('close')">
      <div class="modal">
        <div class="modal-title">{{ title }}</div>

        <div class="field">
          <label>Name</label>
          <input v-model="form.name" type="text" placeholder="e.g. Netflix, Car Payment">
        </div>

        <div class="field-row">
          <div class="field">
            <label>Amount ($)</label>
            <input v-model.number="form.rawAmount" type="number" step="0.01" placeholder="0.00">
          </div>
          <div class="field">
            <label>Type</label>
            <select v-model="form.type">
              <option value="expense">Expense</option>
              <option value="income">Income</option>
            </select>
          </div>
        </div>

        <div class="field-row">
          <div class="field">
            <label>Frequency</label>
            <select v-model="form.frequency">
              <option value="monthly">Monthly</option>
              <option value="biweekly">Biweekly</option>
              <option value="weekly">Weekly</option>
              <option value="daily">Daily</option>
              <option value="once">One-Time</option>
            </select>
          </div>
          <div v-if="form.frequency === 'monthly'" class="field">
            <label>Day of Month</label>
            <input v-model.number="form.dayOfMonth" type="number" min="1" max="31" placeholder="1">
          </div>
          <div v-if="form.frequency === 'once'" class="field">
            <label>Date</label>
            <input v-model="form.oneTimeDate" type="date">
          </div>
          <div v-if="form.frequency === 'biweekly' || form.frequency === 'weekly'" class="field">
            <label>Starting From</label>
            <input v-model="form.anchorDate" type="date">
          </div>
        </div>

        <div class="field">
          <label>Start Date</label>
          <input v-model="form.startDate" type="date">
        </div>

        <div class="modal-actions">
          <button class="btn btn-cancel" @click="emit('close')">Cancel</button>
          <button class="btn btn-save" @click="handleSave" :disabled="saving">
            {{ saving ? 'Saving...' : 'Save' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { reactive, ref, watch, computed } from 'vue'
import type { CommitmentCreate, Frequency } from '@/types/commitment'
import { toLocalDateString } from '@/utils/format'

const props = defineProps<{
  visible: boolean
  editData?: { id: number; name: string; amount: string; frequency: string; day_of_month: number | null; anchor_date: string | null; one_time_date: string | null; start_date: string } | null
}>()

const emit = defineEmits<{
  close: []
  save: [data: CommitmentCreate, editId?: number]
}>()

const saving = ref(false)

const form = reactive({
  name: '',
  rawAmount: 0,
  type: 'expense' as 'expense' | 'income',
  frequency: 'monthly' as Frequency,
  dayOfMonth: 1,
  anchorDate: '',
  oneTimeDate: '',
  startDate: toLocalDateString(new Date()),
})

const title = computed(() => props.editData ? 'Edit Commitment' : 'Add Commitment')

watch(() => props.visible, (vis) => {
  if (!vis) return

  if (props.editData) {
    const d = props.editData
    const amt = Number(d.amount)
    form.name = d.name
    form.rawAmount = Math.abs(amt)
    form.type = amt >= 0 ? 'income' : 'expense'
    form.frequency = d.frequency as Frequency
    form.dayOfMonth = d.day_of_month ?? 1
    form.anchorDate = d.anchor_date ?? ''
    form.oneTimeDate = d.one_time_date ?? ''
    form.startDate = d.start_date
  } else {
    form.name = ''
    form.rawAmount = 0
    form.type = 'expense'
    form.frequency = 'monthly'
    form.dayOfMonth = 1
    form.anchorDate = ''
    form.oneTimeDate = ''
    form.startDate = toLocalDateString(new Date())
  }
})

async function handleSave() {
  if (!form.name || form.rawAmount <= 0) return

  saving.value = true
  try {
    const signedAmount = form.type === 'expense' ? -form.rawAmount : form.rawAmount

    const data: CommitmentCreate = {
      name: form.name,
      amount: String(signedAmount),
      frequency: form.frequency,
      start_date: form.startDate,
      is_paycheck: false,
    }

    if (form.frequency === 'monthly') {
      data.day_of_month = form.dayOfMonth
    } else if (form.frequency === 'once') {
      data.one_time_date = form.oneTimeDate
    } else if (form.frequency === 'biweekly' || form.frequency === 'weekly') {
      data.anchor_date = form.anchorDate
    } else if (form.frequency === 'daily') {
      data.anchor_date = form.startDate
    }

    emit('save', data, props.editData?.id)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(6, 8, 12, 0.85);
  backdrop-filter: blur(8px);
  z-index: 100;
  display: none;
  align-items: center;
  justify-content: center;
}

.modal-overlay.show {
  display: flex;
}

.modal {
  backdrop-filter: blur(24px);
  background: rgba(14, 17, 24, 0.95);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  padding: 28px;
  width: 420px;
  max-width: 90vw;
  box-shadow: var(--shadow-modal);
}

.modal-title {
  font-size: 16px;
  font-weight: 800;
  color: var(--bright);
  margin-bottom: 20px;
}

.field {
  margin-bottom: 14px;
}

.field label {
  display: block;
  font-size: 9px;
  font-weight: 700;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 5px;
}

.field input,
.field select {
  width: 100%;
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  color: var(--bright);
  font-family: var(--font-sans);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}

.field input:focus,
.field select:focus {
  border-color: rgba(167, 139, 250, 0.3);
}

.field select {
  cursor: pointer;
  appearance: none;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  justify-content: flex-end;
}

.btn {
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid var(--border);
  transition: all 0.15s;
}

.btn-cancel {
  background: none;
  color: var(--dim);
}

.btn-cancel:hover {
  color: var(--text);
  background: var(--raised);
}

.btn-save {
  background: rgba(167, 139, 250, 0.15);
  color: var(--income);
  border-color: rgba(167, 139, 250, 0.2);
}

.btn-save:hover {
  background: rgba(167, 139, 250, 0.25);
}

.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
