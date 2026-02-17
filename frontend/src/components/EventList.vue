<template>
  <div>
    <div class="sh">
      <span class="sh-t">Upcoming Events</span>
      <span class="sh-m">{{ eventCount }} events</span>
    </div>

    <div v-for="group in groupedEvents" :key="group.month" class="ev-box">
      <div class="ev-month">{{ group.month }}</div>
      <div class="ev-hdr">
        <span>Day</span>
        <span>Name</span>
        <span>Amount</span>
        <span>Balance</span>
      </div>
      <div
        v-for="(ev, idx) in group.events"
        :key="`${ev.date}-${ev.name}-${idx}`"
        class="ev-r"
        :class="{ inc: ev.amount > 0 }"
        @mouseenter="emit('hoverDate', ev.date)"
        @mouseleave="emit('hoverDate', null)"
        @click="emit('clickDate', ev.date)"
      >
        <span class="ev-d">{{ shortDay(ev.date) }}</span>
        <span class="ev-n" :class="{ inc: ev.amount > 0 }">{{ ev.name }}</span>
        <span class="ev-a" :class="ev.amount > 0 ? 'pos' : 'neg'">
          {{ ev.amount > 0 ? '+' : '-' }}{{ fmtShort(ev.amount) }}
        </span>
        <span class="ev-b">{{ fmtShort(ev.balance) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ParsedLedgerEntry } from '@/types/projection'
import { parseLocalDate } from '@/utils/format'

const props = defineProps<{
  ledger: ParsedLedgerEntry[]
}>()

const emit = defineEmits<{
  hoverDate: [date: string | null]
  clickDate: [date: string]
}>()

interface EventRow {
  date: string
  name: string
  amount: number
  balance: number
}

interface MonthGroup {
  month: string
  events: EventRow[]
}

const fmtShort = (n: number) =>
  '$' + Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const shortDay = (d: string) =>
  parseLocalDate(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })

const eventCount = computed(() => props.ledger.length)

const groupedEvents = computed<MonthGroup[]>(() => {
  const groups = new Map<string, EventRow[]>()

  for (const entry of props.ledger) {
    const dt = parseLocalDate(entry.date)
    const monthKey = dt.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })

    if (!groups.has(monthKey)) {
      groups.set(monthKey, [])
    }
    groups.get(monthKey)!.push({
      date: entry.date,
      name: entry.name,
      amount: entry.delta,
      balance: entry.balance,
    })
  }

  return Array.from(groups.entries()).map(([month, events]) => ({ month, events }))
})
</script>

<style scoped>
.sh {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin: 20px 0 10px;
}

.sh-t {
  font-size: 10px;
  font-weight: 700;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.sh-m {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--muted);
}

.ev-box {
  backdrop-filter: blur(16px);
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: 14px;
  box-shadow: var(--shadow-card);
}

.ev-month {
  padding: 10px 18px;
  font-size: 9px;
  font-weight: 700;
  color: var(--dim);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  background: var(--raised);
  border-bottom: 1px solid var(--border);
}

.ev-hdr {
  display: grid;
  grid-template-columns: 44px 1fr auto 80px;
  gap: 10px;
  padding: 9px 18px;
  border-bottom: 1px solid var(--border);
  font-size: 8px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.ev-r {
  display: grid;
  grid-template-columns: 44px 1fr auto 80px;
  gap: 10px;
  align-items: center;
  padding: 7px 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.02);
  font-size: 12px;
  transition: background 0.15s;
  cursor: default;
}

.ev-r:last-child { border-bottom: none; }
.ev-r:hover { background: rgba(255, 255, 255, 0.02); }
.ev-r.inc { background: rgba(167, 139, 250, 0.03); }
.ev-r.inc:hover { background: rgba(167, 139, 250, 0.06); }

.ev-d {
  font-family: var(--font-mono);
  font-weight: 600;
  text-align: center;
  color: var(--dim);
  font-size: 11px;
}

.ev-n { color: var(--text); }
.ev-n.inc { color: var(--income); }

.ev-a {
  font-family: var(--font-mono);
  font-weight: 700;
  text-align: right;
  font-size: 12px;
}

.ev-a.pos { color: var(--income); }
.ev-a.neg { color: var(--danger); }

.ev-b {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--dim);
  text-align: right;
}

@media (max-width: 700px) {
  .ev-hdr, .ev-r {
    grid-template-columns: 36px 1fr auto;
  }
  .ev-b, .ev-hdr > span:last-child {
    display: none;
  }
}
</style>
