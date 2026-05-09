<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h5 flex-grow-1">Aufträge</h1>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreate">Neuer Auftrag</v-btn>
    </div>

    <div class="d-flex gap-2 mb-4 flex-wrap">
      <v-text-field v-model="search" prepend-inner-icon="mdi-magnify" label="Titel oder Nr." clearable variant="outlined" density="compact" style="max-width:300px" @update:model-value="onSearch" />
      <v-select v-model="statusFilter" :items="statusOptions" label="Status" variant="outlined" density="compact" clearable style="max-width:200px" @update:model-value="() => { page = 1; load() }" />
    </div>

    <v-card>
      <v-table>
        <thead>
          <tr>
            <th>Auftragsnr.</th>
            <th>Titel</th>
            <th>Status</th>
            <th>Start</th>
            <th class="text-right">Ist-Std.</th>
            <th class="text-right">Budget-Std.</th>
            <th class="text-right">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="7" class="text-center pa-4"><v-progress-circular indeterminate size="24" /></td></tr>
          <tr v-else-if="!items.length"><td colspan="7" class="text-center pa-4 text-medium-emphasis">Keine Aufträge</td></tr>
          <tr v-for="o in items" :key="o.id" style="cursor:pointer" @click="openDetail(o)">
            <td><strong>{{ o.order_no }}</strong></td>
            <td>{{ o.title }}</td>
            <td><v-chip :color="STATUS_COLORS[o.status]" size="small" label>{{ STATUS_LABELS[o.status] }}</v-chip></td>
            <td>{{ o.start_date ? fmtDate(o.start_date) : '—' }}</td>
            <td class="text-right">{{ o.hours_total.toFixed(1) }}</td>
            <td class="text-right">{{ o.budget_hours ?? '—' }}</td>
            <td class="text-right" @click.stop>
              <v-btn icon size="small" variant="text" @click="openDetail(o)"><v-icon>mdi-clock-outline</v-icon><v-tooltip activator="parent">Stunden</v-tooltip></v-btn>
              <v-btn icon size="small" variant="text" @click="openEdit(o)"><v-icon>mdi-pencil</v-icon></v-btn>
              <v-btn icon size="small" variant="text" color="error" @click="askDelete(o)"><v-icon>mdi-delete</v-icon></v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
      <div class="d-flex align-center justify-space-between pa-3">
        <span class="text-caption text-medium-emphasis">{{ total }} Aufträge</span>
        <div class="d-flex align-center">
          <v-btn size="small" variant="text" :disabled="page === 1" @click="page--"><v-icon>mdi-chevron-left</v-icon></v-btn>
          <span class="text-caption">{{ page }} / {{ totalPages }}</span>
          <v-btn size="small" variant="text" :disabled="page >= totalPages" @click="page++"><v-icon>mdi-chevron-right</v-icon></v-btn>
        </div>
      </div>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="dialog" max-width="600" persistent>
      <v-card>
        <v-card-title>{{ editItem ? 'Auftrag bearbeiten' : 'Neuer Auftrag' }}</v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-row dense>
              <v-col cols="12"><v-text-field v-model="form.title" label="Titel *" :rules="[required]" variant="outlined" density="compact" /></v-col>
              <v-col cols="12" sm="6">
                <v-autocomplete v-model="form.customer_id" :items="customers" item-title="name" item-value="id" label="Kunde *" :rules="[required]" variant="outlined" density="compact" :loading="customersLoading" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-select v-model="form.status" :items="statusOptions" label="Status" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="6"><v-text-field v-model="form.start_date" label="Start" type="date" variant="outlined" density="compact" /></v-col>
              <v-col cols="12" sm="6"><v-text-field v-model="form.end_date" label="Ende" type="date" variant="outlined" density="compact" /></v-col>
              <v-col cols="12" sm="6"><v-text-field v-model="form.budget_hours" label="Budget Stunden" type="number" step="0.5" variant="outlined" density="compact" /></v-col>
              <v-col cols="12" sm="6"><v-text-field v-model="form.budget_material" label="Budget Material €" type="number" step="0.01" variant="outlined" density="compact" /></v-col>
              <v-col cols="12"><v-textarea v-model="form.notes" label="Notizen" rows="2" variant="outlined" density="compact" /></v-col>
            </v-row>
          </v-form>
          <v-alert v-if="formError" type="error" variant="tonal" density="compact" class="mt-2">{{ formError }}</v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Abbrechen</v-btn>
          <v-btn color="primary" variant="flat" :loading="saving" @click="save">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Time entries detail dialog -->
    <v-dialog v-model="detailDialog" max-width="700">
      <v-card v-if="selectedOrder">
        <v-card-title>{{ selectedOrder.order_no }} — Stundenerfassung</v-card-title>
        <v-card-text>
          <div class="mb-3 d-flex gap-4">
            <div class="text-center"><div class="text-caption text-medium-emphasis">Ist</div><div class="text-h6">{{ selectedOrder.hours_total.toFixed(1) }} h</div></div>
            <div class="text-center"><div class="text-caption text-medium-emphasis">Verrechenbar</div><div class="text-h6">{{ selectedOrder.hours_billable.toFixed(1) }} h</div></div>
            <div v-if="selectedOrder.budget_hours" class="text-center"><div class="text-caption text-medium-emphasis">Budget</div><div class="text-h6">{{ selectedOrder.budget_hours }} h</div></div>
          </div>

          <v-table density="compact" class="mb-3">
            <thead><tr><th>Datum</th><th class="text-right">Std.</th><th>Beschreibung</th><th>Verr.</th><th></th></tr></thead>
            <tbody>
              <tr v-if="!timeEntries.length"><td colspan="5" class="text-center pa-3 text-medium-emphasis">Noch keine Einträge</td></tr>
              <tr v-for="e in timeEntries" :key="e.id">
                <td>{{ fmtDate(e.entry_date) }}</td>
                <td class="text-right">{{ e.hours }}</td>
                <td>{{ e.description ?? '—' }}</td>
                <td><v-icon :color="e.billable ? 'success' : 'default'" size="small">{{ e.billable ? 'mdi-check' : 'mdi-minus' }}</v-icon></td>
                <td><v-btn icon size="x-small" variant="text" color="error" @click="deleteEntry(e)"><v-icon>mdi-delete</v-icon></v-btn></td>
              </tr>
            </tbody>
          </v-table>

          <!-- Quick-add -->
          <v-card variant="tonal" class="pa-3">
            <div class="text-subtitle-2 mb-2">Schnellbuchung</div>
            <v-row dense>
              <v-col cols="4"><v-text-field v-model="newEntry.entry_date" type="date" label="Datum" variant="outlined" density="compact" /></v-col>
              <v-col cols="3"><v-text-field v-model="newEntry.hours" type="number" step="0.25" min="0.25" label="Stunden" variant="outlined" density="compact" /></v-col>
              <v-col cols="5"><v-text-field v-model="newEntry.description" label="Beschreibung" variant="outlined" density="compact" /></v-col>
              <v-col cols="6"><v-checkbox v-model="newEntry.billable" label="Verrechenbar" density="compact" hide-details /></v-col>
              <v-col cols="6" class="d-flex align-center justify-end">
                <v-btn color="primary" size="small" :loading="addingEntry" @click="addEntry">Buchen</v-btn>
              </v-col>
            </v-row>
          </v-card>
        </v-card-text>
        <v-card-actions><v-spacer /><v-btn variant="text" @click="detailDialog = false">Schließen</v-btn></v-card-actions>
      </v-card>
    </v-dialog>

    <ConfirmDialog ref="confirmRef" title="Auftrag löschen?" :message="`${deleteTarget?.title} löschen?`" @confirm="doDelete" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ordersApi, type Order, type TimeEntry, STATUS_LABELS, STATUS_COLORS } from '@/api/orders'
import { customersApi, type Customer } from '@/api/stammdaten'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const LIMIT = 25
const items = ref<Order[]>([])
const total = ref(0)
const loading = ref(false)
const search = ref('')
const statusFilter = ref<string | null>(null)
const page = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / LIMIT)))
const dialog = ref(false)
const saving = ref(false)
const formError = ref('')
const formRef = ref()
const editItem = ref<Order | null>(null)
const deleteTarget = ref<Order | null>(null)
const confirmRef = ref()
const customers = ref<Customer[]>([])
const customersLoading = ref(false)
const detailDialog = ref(false)
const selectedOrder = ref<Order | null>(null)
const timeEntries = ref<TimeEntry[]>([])
const addingEntry = ref(false)

const today = new Date().toISOString().slice(0, 10)
const newEntry = ref({ entry_date: today, hours: '1.00', description: '', billable: true })

const statusOptions = [
  { title: 'Offen', value: 'open' }, { title: 'In Arbeit', value: 'in_progress' },
  { title: 'Abgeschlossen', value: 'done' }, { title: 'Storniert', value: 'cancelled' },
]
const required = (v: unknown) => !!v || 'Pflichtfeld'
const fmtDate = (d: string) => new Date(d).toLocaleDateString('de-DE')

const form = ref({ title: '', customer_id: null as number | null, status: 'open' as import('@/api/orders').OrderStatus, start_date: '', end_date: '', budget_hours: '', budget_material: '', notes: '' })

async function load() {
  loading.value = true
  try {
    const res = await ordersApi.list({ skip: (page.value - 1) * LIMIT, limit: LIMIT, search: search.value || undefined, status: statusFilter.value || undefined })
    items.value = res.items; total.value = res.total
  } finally { loading.value = false }
}

let t: ReturnType<typeof setTimeout>
function onSearch() { clearTimeout(t); t = setTimeout(() => { page.value = 1; load() }, 300) }
watch(page, load)
onMounted(async () => {
  customersLoading.value = true
  try { customers.value = (await customersApi.list({ limit: 500 })).items } finally { customersLoading.value = false }
  load()
})

function openCreate() { editItem.value = null; Object.assign(form.value, { title: '', customer_id: null, status: 'open', start_date: '', end_date: '', budget_hours: '', budget_material: '', notes: '' }); formError.value = ''; dialog.value = true }
function openEdit(o: Order) {
  editItem.value = o
  Object.assign(form.value, { title: o.title, customer_id: o.customer_id, status: o.status, start_date: o.start_date ?? '', end_date: o.end_date ?? '', budget_hours: o.budget_hours ?? '', budget_material: o.budget_material ?? '', notes: o.notes ?? '' })
  formError.value = ''; dialog.value = true
}
async function save() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  saving.value = true; formError.value = ''
  try {
    const payload = { ...form.value, customer_id: form.value.customer_id!, start_date: form.value.start_date || null, end_date: form.value.end_date || null, budget_hours: form.value.budget_hours || null, budget_material: form.value.budget_material || null, notes: form.value.notes || null }
    editItem.value ? await ordersApi.update(editItem.value.id, payload) : await ordersApi.create(payload as Parameters<typeof ordersApi.create>[0])
    dialog.value = false; load()
  } catch (e) { formError.value = e instanceof Error ? e.message : 'Fehler' }
  finally { saving.value = false }
}
function askDelete(o: Order) { deleteTarget.value = o; confirmRef.value.open() }
async function doDelete() {
  if (!deleteTarget.value) return
  try { await ordersApi.delete(deleteTarget.value.id); confirmRef.value.close(); load() }
  catch { confirmRef.value.close() }
}
async function openDetail(o: Order) {
  selectedOrder.value = o; detailDialog.value = true
  timeEntries.value = await ordersApi.timeEntries(o.id)
}
async function addEntry() {
  if (!selectedOrder.value || !newEntry.value.hours) return
  addingEntry.value = true
  try {
    await ordersApi.addTime(selectedOrder.value.id, { ...newEntry.value })
    timeEntries.value = await ordersApi.timeEntries(selectedOrder.value.id)
    newEntry.value = { entry_date: today, hours: '1.00', description: '', billable: true }
    const updated = await ordersApi.get(selectedOrder.value.id)
    selectedOrder.value = updated
    load()
  } finally { addingEntry.value = false }
}
async function deleteEntry(e: TimeEntry) {
  if (!selectedOrder.value) return
  await ordersApi.deleteTime(selectedOrder.value.id, e.id)
  timeEntries.value = await ordersApi.timeEntries(selectedOrder.value.id)
  const updated = await ordersApi.get(selectedOrder.value.id)
  selectedOrder.value = updated
  load()
}
</script>
