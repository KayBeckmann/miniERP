<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h5 flex-grow-1">Angebote</h1>
      <v-btn color="primary" prepend-icon="mdi-plus" :to="{ name: 'quote-new' }">Neues Angebot</v-btn>
    </div>
    <div class="d-flex gap-2 mb-4 flex-wrap">
      <v-text-field v-model="search" prepend-inner-icon="mdi-magnify" label="Angebotsnr. oder Kunde"
        clearable variant="outlined" density="compact" style="max-width:320px" @update:model-value="onSearch" />
      <v-select v-model="statusFilter" :items="statusOptions" label="Status" variant="outlined"
        density="compact" clearable style="max-width:200px" @update:model-value="() => { page = 1; load() }" />
    </div>
    <v-card>
      <v-table>
        <thead>
          <tr>
            <th>Angebotsnr.</th><th>Datum</th><th>Gültig bis</th><th>Gruppen</th>
            <th>Status</th><th class="text-right">Betrag</th><th class="text-right">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="7" class="text-center pa-4"><v-progress-circular indeterminate size="24" /></td></tr>
          <tr v-else-if="!items.length"><td colspan="7" class="text-center pa-4 text-medium-emphasis">Keine Angebote</td></tr>
          <tr v-for="q in items" :key="q.id" style="cursor:pointer" @click="openEditor(q.id)">
            <td><strong>{{ q.quote_no }}</strong></td>
            <td>{{ fmtDate(q.date) }}</td>
            <td>{{ q.valid_until ? fmtDate(q.valid_until) : '—' }}</td>
            <td><span class="text-caption">{{ q.groups.length ? q.groups.map(g => g.title).join(' · ') : `${totalItems(q)} Pos.` }}</span></td>
            <td><v-chip :color="STATUS_COLORS[q.status]" size="small" label>{{ STATUS_LABELS[q.status] }}</v-chip></td>
            <td class="text-right"><strong>{{ fmtEur(q.total) }}</strong></td>
            <td class="text-right" @click.stop>
              <v-btn icon size="small" variant="text" :to="{ name: 'quote-edit', params: { id: q.id } }"><v-icon>mdi-pencil</v-icon></v-btn>
              <v-btn v-if="q.status === 'accepted'" icon size="small" variant="text" color="success" title="In Auftrag wandeln" @click="openToOrder(q)"><v-icon>mdi-briefcase-arrow-right</v-icon></v-btn>
              <v-btn icon size="small" variant="text" title="Kopieren" @click="doDuplicate(q)"><v-icon>mdi-content-copy</v-icon></v-btn>
              <v-btn v-if="q.status === 'draft'" icon size="small" variant="text" color="error" @click="askDelete(q)"><v-icon>mdi-delete</v-icon></v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
      <div class="d-flex align-center justify-space-between pa-3">
        <span class="text-caption text-medium-emphasis">{{ total }} Angebote</span>
        <div class="d-flex align-center">
          <v-btn size="small" variant="text" :disabled="page === 1" @click="page--"><v-icon>mdi-chevron-left</v-icon></v-btn>
          <span class="text-caption">{{ page }} / {{ totalPages }}</span>
          <v-btn size="small" variant="text" :disabled="page >= totalPages" @click="page++"><v-icon>mdi-chevron-right</v-icon></v-btn>
        </div>
      </div>
    </v-card>

    <v-dialog v-model="toOrderDialog" max-width="460">
      <v-card v-if="toOrderTarget">
        <v-card-title>In Auftrag wandeln — {{ toOrderTarget.quote_no }}</v-card-title>
        <v-card-text>
          <v-text-field v-model="orderTitle" label="Auftragsbezeichnung (leer = automatisch)" variant="outlined" density="compact" class="mb-2" />
          <v-alert type="info" variant="tonal" density="compact">Ein neuer Auftrag wird angelegt und mit diesem Angebot verknüpft.</v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="toOrderDialog = false">Abbrechen</v-btn>
          <v-btn color="success" variant="flat" :loading="converting" @click="doConvertToOrder">Auftrag erstellen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <ConfirmDialog ref="confirmRef" title="Angebot löschen?" :message="`Angebot ${deleteTarget?.quote_no} löschen?`" @confirm="doDelete" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { quotesApi, type Quote, STATUS_LABELS, STATUS_COLORS } from '@/api/quotes'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const router = useRouter()
const LIMIT = 25
const items = ref<Quote[]>([])
const total = ref(0)
const loading = ref(false)
const search = ref('')
const statusFilter = ref<string | null>(null)
const page = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / LIMIT)))
const deleteTarget = ref<Quote | null>(null)
const confirmRef = ref()
const toOrderDialog = ref(false)
const toOrderTarget = ref<Quote | null>(null)
const orderTitle = ref('')
const converting = ref(false)

const statusOptions = [
  { title: 'Entwurf', value: 'draft' }, { title: 'Gesendet', value: 'sent' },
  { title: 'Angenommen', value: 'accepted' }, { title: 'Abgelehnt', value: 'declined' },
  { title: 'Abgelaufen', value: 'expired' },
]

async function load() {
  loading.value = true
  try {
    const res = await quotesApi.list({ skip: (page.value - 1) * LIMIT, limit: LIMIT, search: search.value || undefined, status: statusFilter.value || undefined })
    items.value = res.items; total.value = res.total
  } finally { loading.value = false }
}
let t: ReturnType<typeof setTimeout>
function onSearch() { clearTimeout(t); t = setTimeout(() => { page.value = 1; load() }, 300) }
watch(page, load)
onMounted(load)

const fmtDate = (d: string) => { if (!d) return '—'; const dt = new Date(d + 'T00:00:00'); return isNaN(dt.getTime()) ? d : dt.toLocaleDateString('de-DE') }
const fmtEur = (v: string) => `${Number(v).toFixed(2)} €`
const totalItems = (q: Quote) => q.groups.reduce((s, g) => s + g.items.length, 0) + q.items.length

function openEditor(id: number) { router.push({ name: 'quote-edit', params: { id } }) }
async function doDuplicate(q: Quote) { try { await quotesApi.duplicate(q.id); load() } catch {} }
function openToOrder(q: Quote) { toOrderTarget.value = q; orderTitle.value = ''; toOrderDialog.value = true }
async function doConvertToOrder() {
  if (!toOrderTarget.value) return
  converting.value = true
  try { await quotesApi.toOrder(toOrderTarget.value.id, orderTitle.value || undefined); toOrderDialog.value = false; router.push({ name: 'orders' }) }
  catch (e) { console.error(e) }
  finally { converting.value = false }
}
function askDelete(q: Quote) { deleteTarget.value = q; confirmRef.value.open() }
async function doDelete() {
  if (!deleteTarget.value) return
  try { await quotesApi.delete(deleteTarget.value.id); confirmRef.value.close(); load() }
  catch { confirmRef.value.close() }
}
</script>
