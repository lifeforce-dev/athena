<template>
  <Teleport to="body">
    <div class="modal-overlay" :class="{ show: visible }">
      <div class="modal">
        <div class="modal-title">{{ title }}</div>

        <div class="field">
          <label>{{ t('modal.name') }}</label>
          <input v-model="form.name" type="text" :placeholder="t('modal.name_placeholder')">
        </div>

        <div class="field-row">
          <div class="field">
            <label>{{ t('modal.amount', { symbol: currencySymbol() }) }}</label>
            <input v-model.number="form.rawAmount" type="number" step="0.01" placeholder="0.00">
          </div>
          <div class="field">
            <label>{{ t('modal.type') }}</label>
            <select v-model="form.type">
              <option value="expense">{{ t('modal.type_expense') }}</option>
              <option value="income">{{ t('modal.type_income') }}</option>
            </select>
          </div>
        </div>

        <div class="field-row">
          <div class="field">
            <label>{{ t('modal.frequency') }}</label>
            <select v-model="form.frequency">
              <option value="monthly">{{ t('freq.monthly') }}</option>
              <option value="biweekly">{{ t('freq.biweekly') }}</option>
              <option value="weekly">{{ t('freq.weekly') }}</option>
              <option value="daily">{{ t('freq.daily') }}</option>
              <option value="once">{{ t('freq.once') }}</option>
            </select>
          </div>
          <div v-if="form.frequency === 'monthly'" class="field">
            <label>{{ t('modal.day_of_month') }}</label>
            <input v-model.number="form.dayOfMonth" type="number" min="1" max="31" placeholder="1">
          </div>
          <div v-if="form.frequency === 'once'" class="field">
            <label>{{ t('modal.date') }}</label>
            <input v-model="form.oneTimeDate" type="date">
          </div>
          <div v-if="form.frequency === 'biweekly' || form.frequency === 'weekly'" class="field">
            <label>{{ t('modal.starting_from') }}</label>
            <input v-model="form.anchorDate" type="date">
          </div>
        </div>

        <div v-if="form.frequency !== 'once'" class="field">
          <label>{{ t('modal.start_date') }}</label>
          <input v-model="form.startDate" type="date">
        </div>

        <div class="modal-actions">
          <button class="btn btn-cancel" @click="emit('close')">{{ t('modal.cancel') }}</button>
          <button class="btn btn-save" @click="handleSave" :disabled="saving">
            {{ saving ? t('modal.saving') : t('modal.save') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { reactive, ref, watch, computed } from 'vue'
import type { CommitmentCreate, Frequency } from '@/types/commitment'
import { toLocalDateString, toDisplayCurrency, currencySymbol } from '@/utils/format'
import { useI18n } from '@/composables/useI18n'

const props = defineProps<{
  visible: boolean
  editData?: { id: number; name: string; amount: string; frequency: string; day_of_month: number | null; anchor_date: string | null; one_time_date: string | null; start_date: string } | null
}>()

const emit = defineEmits<{
  close: []
  save: [data: CommitmentCreate, editId?: number]
}>()

const saving = ref(false)
const { t } = useI18n()

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

const title = computed(() => props.editData ? t('modal.edit_title') : t('modal.add_title'))

watch(() => props.visible, (isVisible) => {
  if (!isVisible) return

  if (props.editData) {
    const existing = props.editData
    const parsedAmount = Number(existing.amount)
    form.name = existing.name
    form.rawAmount = toDisplayCurrency(Math.abs(parsedAmount))
    form.type = parsedAmount >= 0 ? 'income' : 'expense'
    form.frequency = existing.frequency as Frequency
    form.dayOfMonth = existing.day_of_month ?? 1
    form.anchorDate = existing.anchor_date ?? ''
    form.oneTimeDate = existing.one_time_date ?? ''
    form.startDate = existing.start_date
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
