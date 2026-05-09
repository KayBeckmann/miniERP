<template>
  <div>
    <div class="d-flex align-center mb-4 gap-2 flex-wrap">
      <h1 class="text-h5 flex-grow-1">Stundenerfassung</h1>
      <v-btn size="small" variant="outlined" @click="prevWeek"><v-icon>mdi-chevron-left</v-icon></v-btn>
      <span class="text-body-2 font-weight-medium">KW {{ weekNum }} · {{ weekLabel }}</span>
      <v-btn size="small" variant="outlined" @click="nextWeek"><v-icon>mdi-chevron-right</v-icon></v-btn>
      <v-btn size="small" variant="text" @click="goToday">Heute</v-btn>
    </div>

    <!-- Wochenübersicht -->
    <v-row class="mb-4">
      <v-col v-for="d in weekDays" :key="d.iso" cols="12" sm="6" md="4" lg>
        <v-card :color="d.isToday ? 'primary' : undefined" :variant="d.isToday ? 'tonal' : 'outlined'" class="pa-3" style="min-height:80px">
          <div class="d-flex align-center justify-space-between mb-1">
            <div>
              <span class="text-caption text-medium-emphasis">{{ d.label }}</span>
              <div class="font-weight-bold">{{ d.date }}</div>
            </div>
            <div class="text-right">
              <span class="text-h6">{{ dayHours(d.iso).toFixed(1) }}</span>
              <span class="text-caption">h</span>
            </div>
          </div>
          <div v-for="e in entriesByDay(d.iso)" :key="e.id" class="d-flex align-center gap-1 mt-1">
            <v-chip size="x-small" :color="e.billable ? 'success' : 'default'" label>{{ e.hours }}h</v-chip>
            <span class="text-caption text-truncate" style="max-width:120px">{{ orderTitle(e.order_id) }}</span>
            <v-btn icon size="x-small" variant="text" color="error" class="ml-auto" @click="removeEntry(e)">
              <v-icon size="12">mdi-close</v-icon>
            </v-btn>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Schnellbuchung -->
    <v-card class="pa-4 mb-4">
      <div class="text-subtitle-2 mb-3">Schnellbuchung</div>
      <v-row dense>
        <v-col cols="12" sm="3">
          <v-text-field v-model="form.entry_date" type="date" label="Datum *" variant="outlined" density="compact" />
        </v-col>
        <v-col cols="12" sm="3">
          <v-autocomplete v-model="form.order_id" :items="orders" item-title="title" item-value="id"
            label="Auftrag *" variant="outlined" density="compact" :loading="ordersLoading">
            <template #item="{ item, props }">
              <v-list-item v-bind="props" :subtitle="item.raw.order_no" />
            </template>
          </v-autocomplete>
        </v-col>
        <v-col cols="12" sm="2">
          <v-text-field v-model="form.hours" type="number" step="0.25" min="0.25" label="Stunden *" variant="outlined" density="compact" />
        </v-col>
        <v-col cols="12" sm="3">
          <v-text-field v-model="form.description" label="Beschreibung" variant="outlined" density="compact" />
        </v-col>
        <v-col cols="12" sm="1" class="d-flex align-center">
          <v-checkbox v-model="form.billable" label="Verr." density="compact" hide-details />
        </v-col>
      </v-row>
      <div class="d-flex align-center gap-2 mt-2">
        <v-btn color="primary" :loading="saving" :disabled="!form.order_id || !form.hours" @click="addEntry">Buchen</v-btn>
        <v-alert v-if="saveError" type="error" variant="tonal" density="compact">{{ saveError }}</v-alert>
      </div>
    </v-card>

    <!-- Wochenstatistik -->
    <v-row>
      <v-col cols="12" md="4">
        <v-card class="pa-3">
          <div class="text-caption text-medium-emphasis">Wochenstunden gesamt</div>
          <div class="text-h5 font-weight-bold">{{ weekTotal.toFixed(1) }} h</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card class="pa-3">
          <div class="text-caption text-medium-emphasis">Verrechenbar</div>
          <div class="text-h5 font-weight-bold text-success">{{ weekBillable.toFixed(1) }} h</div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card class="pa-3">
          <div class="text-caption text-medium-emphasis">Nicht verrechenbar</div>
          <div class="text-h5 font-weight-bold text-medium-emphasis">{{ (weekTotal - weekBillable).toFixed(1) }} h</div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Detailansicht -->
    <v-card class="mt-4">
      <v-table density="compact">
        <thead>
          <tr><th>Datum</th><th>Auftrag</th><th class="text-right">Std.</th><th>Beschreibung</th><th>Verr.</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="6" class="text-center pa-4"><v-progress-circular indeterminate size="20" /></td></tr>
          <tr v-else-if="!entries.length"><td colspan="6" class="text-center pa-4 text-medium-emphasis">Keine Einträge in dieser Woche</td></tr>
          <tr v-for="e in entriesSorted" :key="e.id">
            <td>{{ fmtDate(e.entry_date) }}</td>
            <td>{{ orderTitle(e.order_id) }}</td>
            <td class="text-right">{{ e.hours }}</td>
            <td>{{ e.description ?? '—' }}</td>
            <td><v-icon :color="e.billable ? 'success' : 'default'" size="small">{{ e.billable ? 'mdi-check' : 'mdi-minus' }}</v-icon></td>
            <td><v-btn icon size="x-small" variant="text" color="error" @click="removeEntry(e)"><v-icon>mdi-delete</v-icon></v-btn></td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '@/api/client'
import { ordersApi, type Order, type TimeEntry } from '@/api/orders'

const loading = ref(false)
const saving = ref(false)
const saveError = ref('')
const entries = ref<TimeEntry[]>([])
const orders = ref<Order[]>([])
const ordersLoading = ref(false)

// ── Week navigation ──────────────────────────────────────────────────────────
function getMonday(d: Date): Date {
  const day = d.getDay(); const diff = d.getDate() - day + (day === 0 ? -6 : 1)
  return new Date(d.getFullYear(), d.getMonth(), diff)
}
const weekStart = ref(getMonday(new Date()))
const weekDays = computed(() => {
  const days = []
  const today = new Date().toISOString().slice(0, 10)
  for (let i = 0; i < 7; i++) {
    const d = new Date(weekStart.value)
    d.setDate(d.getDate() + i)
    const iso = d.toISOString().slice(0, 10)
    days.push({
      iso,
      label: d.toLocaleDateString('de-DE', { weekday: 'short' }),
      date: d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' }),
      isToday: iso === today,
    })
  }
  return days
})

const weekEnd = computed(() => {
  const d = new Date(weekStart.value); d.setDate(d.getDate() + 6); return d.toISOString().slice(0, 10)
})
const weekLabel = computed(() => {
  const s = weekStart.value.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })
  const e = new Date(weekEnd.value).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: '2-digit' })
  return `${s} – ${e}`
})
const weekNum = computed(() => {
  const d = new Date(weekStart.value)
  d.setHours(0, 0, 0, 0)
  d.setDate(d.getDate() + 4 - (d.getDay() || 7))
  const y = new Date(d.getFullYear(), 0, 1)
  return Math.ceil(((d.getTime() - y.getTime()) / 86400000 + 1) / 7)
})

function prevWeek() { const d = new Date(weekStart.value); d.setDate(d.getDate() - 7); weekStart.value = d }
function nextWeek() { const d = new Date(weekStart.value); d.setDate(d.getDate() + 7); weekStart.value = d }
function goToday() { weekStart.value = getMonday(new Date()) }

// ── Data ────────────────────────────────────────────────────────────────────
const today = new Date().toISOString().slice(0, 10)
const form = ref({ entry_date: today, order_id: null as number | null, hours: '1.00', description: '', billable: true })

async function loadEntries() {
  loading.value = true
  try {
    const res = await api.get<TimeEntry[]>(`/orders/time-entries?from=${weekStart.value.toISOString().slice(0, 10)}&to=${weekEnd.value}`)
    entries.value = res
  } catch { entries.value = [] }
  finally { loading.value = false }
}

watch(weekStart, loadEntries)

onMounted(async () => {
  ordersLoading.value = true
  try {
    const res = await ordersApi.list({ limit: 500, status: 'open' })
    const inProgress = await ordersApi.list({ limit: 500, status: 'in_progress' })
    orders.value = [...res.items, ...inProgress.items]
  } finally { ordersLoading.value = false }
  await loadEntries()
})

const entriesByDay = (iso: string) => entries.value.filter(e => e.entry_date === iso)
const dayHours = (iso: string) => entriesByDay(iso).reduce((s, e) => s + parseFloat(String(e.hours)), 0)
const entriesSorted = computed(() => [...entries.value].sort((a, b) => b.entry_date.localeCompare(a.entry_date)))
const weekTotal = computed(() => entries.value.reduce((s, e) => s + parseFloat(String(e.hours)), 0))
const weekBillable = computed(() => entries.value.filter(e => e.billable).reduce((s, e) => s + parseFloat(String(e.hours)), 0))

const orderMap = computed(() => Object.fromEntries(orders.value.map(o => [o.id, `${o.order_no} · ${o.title}`])))
const orderTitle = (id: number) => orderMap.value[id] ?? `Auftrag #${id}`

const fmtDate = (d: string) => new Date(d + 'T00:00:00').toLocaleDateString('de-DE')

async function addEntry() {
  if (!form.value.order_id || !form.value.hours) return
  saving.value = true; saveError.value = ''
  try {
    await ordersApi.addTime(form.value.order_id, {
      entry_date: form.value.entry_date,
      hours: form.value.hours,
      description: form.value.description || undefined,
      billable: form.value.billable,
    })
    await loadEntries()
    form.value = { entry_date: today, order_id: form.value.order_id, hours: '1.00', description: '', billable: true }
  } catch (e) { saveError.value = e instanceof Error ? e.message : 'Fehler' }
  finally { saving.value = false }
}

async function removeEntry(e: TimeEntry) {
  try { await ordersApi.deleteTime(e.order_id, e.id); await loadEntries() }
  catch {}
}
</script>
