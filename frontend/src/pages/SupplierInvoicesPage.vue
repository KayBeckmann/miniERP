<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h5 flex-grow-1">Eingangsrechnungen</h1>
      <v-btn color="primary" prepend-icon="mdi-upload" @click="uploadDialog = true">
        Rechnung hochladen
      </v-btn>
    </div>

    <!-- Status-Filter -->
    <div class="d-flex gap-2 mb-4">
      <v-select v-model="statusFilter" :items="statusOptions" label="Status" variant="outlined"
        density="compact" clearable style="max-width:200px"
        @update:model-value="() => { page = 1; load() }" />
    </div>

    <v-card>
      <v-table>
        <thead>
          <tr>
            <th>Datei / Paperless-ID</th>
            <th>Rechnungsnr.</th>
            <th>Datum</th>
            <th>Fällig</th>
            <th>Status</th>
            <th class="text-right">Betrag</th>
            <th>KI-Vorschlag</th>
            <th class="text-right">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="8" class="text-center pa-4"><v-progress-circular indeterminate size="24" /></td></tr>
          <tr v-else-if="!items.length"><td colspan="8" class="text-center pa-4 text-medium-emphasis">Keine Eingangsrechnungen</td></tr>
          <tr v-for="si in items" :key="si.id">
            <td>
              <div class="text-caption">{{ si.original_filename ?? '—' }}</div>
              <div v-if="si.paperless_document_id" class="text-caption text-medium-emphasis">Paperless #{{ si.paperless_document_id }}</div>
            </td>
            <td>{{ si.external_no ?? '—' }}</td>
            <td>{{ si.invoice_date ? fmtDate(si.invoice_date) : '—' }}</td>
            <td>{{ si.due_date ? fmtDate(si.due_date) : '—' }}</td>
            <td>
              <v-chip :color="statusColor(si.status)" size="small" label>
                {{ statusLabel(si.status) }}
              </v-chip>
            </td>
            <td class="text-right">{{ si.total ? fmtEur(si.total) : '—' }}</td>
            <td>
              <v-chip v-if="si.ocr_payload && Object.keys(si.ocr_payload).length" color="success" size="x-small" variant="tonal">KI</v-chip>
            </td>
            <td class="text-right">
              <v-btn icon size="small" variant="text" @click="openEdit(si)">
                <v-icon>mdi-pencil</v-icon>
                <v-tooltip activator="parent">Bearbeiten / Bestätigen</v-tooltip>
              </v-btn>
              <v-btn v-if="si.status === 'confirmed'" icon size="small" variant="text" color="success" @click="markPaid(si)">
                <v-icon>mdi-cash-check</v-icon>
                <v-tooltip activator="parent">Als bezahlt markieren</v-tooltip>
              </v-btn>
              <v-btn v-if="si.paperless_document_id" icon size="small" variant="text" @click="openInPaperless(si)">
                <v-icon>mdi-open-in-new</v-icon>
                <v-tooltip activator="parent">In Paperless öffnen</v-tooltip>
              </v-btn>
              <v-btn v-if="si.status === 'draft'" icon size="small" variant="text" color="error" @click="askDelete(si)">
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
      <div class="d-flex align-center justify-space-between pa-3">
        <span class="text-caption text-medium-emphasis">{{ total }} Eingangsrechnungen</span>
        <div class="d-flex align-center">
          <v-btn size="small" variant="text" :disabled="page === 1" @click="page--"><v-icon>mdi-chevron-left</v-icon></v-btn>
          <span class="text-caption">{{ page }} / {{ totalPages }}</span>
          <v-btn size="small" variant="text" :disabled="page >= totalPages" @click="page++"><v-icon>mdi-chevron-right</v-icon></v-btn>
        </div>
      </div>
    </v-card>

    <!-- Upload Dialog -->
    <v-dialog v-model="uploadDialog" max-width="520" persistent>
      <v-card>
        <v-card-title>Rechnung hochladen</v-card-title>
        <v-card-text>
          <v-file-input
            v-model="uploadFile"
            label="PDF, Foto oder Scan auswählen"
            accept=".pdf,.jpg,.jpeg,.png,.tiff"
            prepend-icon="mdi-paperclip"
            variant="outlined"
            density="compact"
            show-size
          />
          <v-alert type="info" variant="tonal" density="compact" class="mt-2">
            Die Datei wird zu Paperless-ngx hochgeladen. OCR und KI-Strukturierung laufen automatisch.
          </v-alert>
          <v-alert v-if="uploadError" type="error" variant="tonal" density="compact" class="mt-2">{{ uploadError }}</v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="uploadDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" variant="flat" :loading="uploading" :disabled="!uploadFile" @click="doUpload">
            Hochladen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Edit / Confirm Dialog -->
    <v-dialog v-model="editDialog" max-width="680" persistent>
      <v-card v-if="editItem">
        <v-card-title class="d-flex align-center">
          Eingangsrechnung bearbeiten
          <v-spacer />
          <v-btn v-if="editItem.paperless_document_id && !restructuring" icon size="small" variant="text"
            title="KI-Strukturierung neu starten" @click="reStructure">
            <v-icon>mdi-robot</v-icon>
          </v-btn>
          <v-progress-circular v-if="restructuring" size="20" indeterminate />
        </v-card-title>

        <!-- KI-Vorschlag Banner -->
        <v-alert v-if="editItem.ocr_payload && Object.keys(editItem.ocr_payload).length" type="success"
          variant="tonal" density="compact" class="mx-4 mb-0">
          KI-Vorschlag vorhanden — bitte prüfen und bestätigen.
        </v-alert>

        <v-card-text>
          <v-row dense>
            <v-col cols="12" sm="6">
              <v-autocomplete v-model="editForm.supplier_id" :items="suppliers" item-title="name"
                item-value="id" label="Lieferant" variant="outlined" density="compact" clearable />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="editForm.external_no" label="Rechnungsnr. (Lieferant)"
                variant="outlined" density="compact" />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="editForm.invoice_date" type="date" label="Rechnungsdatum"
                variant="outlined" density="compact" />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field v-model="editForm.due_date" type="date" label="Fällig bis"
                variant="outlined" density="compact" />
            </v-col>
            <v-col cols="12" sm="4">
              <v-text-field v-model="editForm.subtotal" type="number" step="0.01" label="Netto €"
                variant="outlined" density="compact" />
            </v-col>
            <v-col cols="12" sm="4">
              <v-text-field v-model="editForm.vat_total" type="number" step="0.01" label="MwSt. €"
                variant="outlined" density="compact" />
            </v-col>
            <v-col cols="12" sm="4">
              <v-text-field v-model="editForm.total" type="number" step="0.01" label="Brutto €"
                variant="outlined" density="compact" />
            </v-col>
            <v-col cols="12">
              <v-autocomplete v-model="editForm.order_id" :items="orders" item-title="title"
                item-value="id" label="Auftrag (optional)" variant="outlined" density="compact" clearable />
            </v-col>
            <v-col cols="12">
              <v-textarea v-model="editForm.description" label="Beschreibung" rows="2"
                variant="outlined" density="compact" />
            </v-col>
          </v-row>

          <!-- OCR-Text Vorschau -->
          <v-expansion-panels v-if="editItem.ocr_payload" class="mt-2">
            <v-expansion-panel title="KI-Rohvorschlag anzeigen">
              <v-expansion-panel-text>
                <pre class="text-caption" style="white-space:pre-wrap">{{ JSON.stringify(editItem.ocr_payload, null, 2) }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-card-text>

        <v-card-actions>
          <v-btn variant="text" @click="editDialog = false">Abbrechen</v-btn>
          <v-spacer />
          <v-btn variant="outlined" :loading="saving" @click="saveEdit('draft')">Entwurf speichern</v-btn>
          <v-btn color="success" variant="flat" :loading="saving" @click="saveEdit('confirmed')">
            Bestätigen &amp; buchen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <ConfirmDialog ref="confirmRef" title="Eingangsrechnung löschen?"
      :message="`${deleteTarget?.original_filename ?? 'Eintrag'} löschen?`" @confirm="doDelete" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/api/client'
import { suppliersApi, type Supplier } from '@/api/stammdaten'
import { ordersApi, type Order } from '@/api/orders'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import { useAppSettings } from '@/composables/useAppSettings'

const auth = useAuthStore()
const { paperlessUrl } = useAppSettings()

interface SupplierInvoice {
  id: number; tenant_id: number; supplier_id: number | null; order_id: number | null
  paperless_document_id: number | null; original_filename: string | null; external_no: string | null
  invoice_date: string | null; due_date: string | null; subtotal: string | null; vat_total: string | null
  total: string | null; paid_at: string | null; description: string | null; status: string
  ocr_payload: Record<string, string> | null; created_at: string; updated_at: string
}

const LIMIT = 25
const items = ref<SupplierInvoice[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / LIMIT)))
const statusFilter = ref<string | null>(null)
const uploadDialog = ref(false)
const uploadFile = ref<File[]>([])
const uploading = ref(false)
const uploadError = ref('')
const editDialog = ref(false)
const editItem = ref<SupplierInvoice | null>(null)
const saving = ref(false)
const restructuring = ref(false)
const deleteTarget = ref<SupplierInvoice | null>(null)
const confirmRef = ref()
const suppliers = ref<Supplier[]>([])
const orders = ref<Order[]>([])

const statusOptions = [
  { title: 'Entwurf', value: 'draft' },
  { title: 'Bestätigt', value: 'confirmed' },
  { title: 'Bezahlt', value: 'paid' },
]

const editForm = ref({
  supplier_id: null as number | null, order_id: null as number | null,
  external_no: '', invoice_date: '', due_date: '',
  subtotal: '', vat_total: '', total: '', description: '',
})

function statusLabel(s: string) { return { draft: 'Entwurf', confirmed: 'Bestätigt', paid: 'Bezahlt' }[s] ?? s }
function statusColor(s: string) { return { draft: 'default', confirmed: 'info', paid: 'success' }[s] ?? 'default' }
const fmtDate = (d: string) => new Date(d).toLocaleDateString('de-DE')
const fmtEur = (v: string | number) => `${Number(v).toFixed(2)} €`

async function load() {
  loading.value = true
  try {
    const q = new URLSearchParams()
    if ((page.value - 1) * LIMIT) q.set('skip', String((page.value - 1) * LIMIT))
    q.set('limit', String(LIMIT))
    if (statusFilter.value) q.set('status', statusFilter.value)
    const res = await api.get<{ items: SupplierInvoice[]; total: number }>(`/supplier-invoices?${q}`)
    items.value = res.items; total.value = res.total
  } finally { loading.value = false }
}

watch(page, load)
onMounted(async () => {
  await Promise.all([
    suppliersApi.list({ limit: 500 }).then(r => { suppliers.value = r.items }),
    ordersApi.list({ limit: 500 }).then(r => { orders.value = r.items }),
  ])
  load()
})

async function doUpload() {
  const file = Array.isArray(uploadFile.value) ? uploadFile.value[0] : uploadFile.value
  if (!file) return
  uploading.value = true; uploadError.value = ''
  try {
    const fd = new FormData()
    fd.append('file', file)
    const token = auth.accessToken
    const tenantId = auth.currentTenant?.id
    const res = await fetch('/api/v1/supplier-invoices', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        ...(tenantId ? { 'X-Tenant-ID': String(tenantId) } : {}),
      },
      body: fd,
    })
    if (!res.ok) { const e = await res.json().catch(() => ({})); uploadError.value = e.detail ?? 'Upload fehlgeschlagen'; return }
    uploadDialog.value = false; uploadFile.value = []; load()
  } catch (e) { uploadError.value = e instanceof Error ? e.message : 'Fehler' }
  finally { uploading.value = false }
}

function openEdit(si: SupplierInvoice) {
  editItem.value = si
  editForm.value = {
    supplier_id: si.supplier_id, order_id: si.order_id,
    external_no: si.external_no ?? '', invoice_date: si.invoice_date ?? '',
    due_date: si.due_date ?? '', subtotal: si.subtotal ?? '',
    vat_total: si.vat_total ?? '', total: si.total ?? '',
    description: si.description ?? '',
  }
  editDialog.value = true
}

async function saveEdit(newStatus: string) {
  if (!editItem.value) return
  saving.value = true
  try {
    await api.patch(`/supplier-invoices/${editItem.value.id}`, {
      ...editForm.value,
      supplier_id: editForm.value.supplier_id || null,
      order_id: editForm.value.order_id || null,
      external_no: editForm.value.external_no || null,
      invoice_date: editForm.value.invoice_date || null,
      due_date: editForm.value.due_date || null,
      subtotal: editForm.value.subtotal || null,
      vat_total: editForm.value.vat_total || null,
      total: editForm.value.total || null,
      description: editForm.value.description || null,
      status: newStatus,
    })
    editDialog.value = false; load()
  } finally { saving.value = false }
}

async function reStructure() {
  if (!editItem.value) return
  restructuring.value = true
  try {
    const result = await api.post<Record<string, string>>(`/supplier-invoices/${editItem.value.id}/structure`, {})
    // Felder aus Vorschlag übernehmen wenn leer
    if (!editForm.value.external_no && result.invoice_number) editForm.value.external_no = result.invoice_number
    if (!editForm.value.invoice_date && result.invoice_date) editForm.value.invoice_date = result.invoice_date
    if (!editForm.value.due_date && result.due_date) editForm.value.due_date = result.due_date
    if (!editForm.value.total && result.total) editForm.value.total = result.total
    if (!editForm.value.subtotal && result.subtotal) editForm.value.subtotal = result.subtotal
    if (!editForm.value.vat_total && result.vat_total) editForm.value.vat_total = result.vat_total
    if (!editForm.value.description && result.description) editForm.value.description = result.description
    // Reload item to update ocr_payload display
    const updated = await api.get<SupplierInvoice>(`/supplier-invoices/${editItem.value.id}`)
    editItem.value = updated
  } finally { restructuring.value = false }
}

function openInPaperless(si: SupplierInvoice) {
  if (si.paperless_document_id) {
    window.open(`${paperlessUrl}/documents/${si.paperless_document_id}/details`, '_blank')
  }
}

function askDelete(si: SupplierInvoice) { deleteTarget.value = si; confirmRef.value.open() }
async function doDelete() {
  if (!deleteTarget.value) return
  try { await api.delete(`/supplier-invoices/${deleteTarget.value.id}`); confirmRef.value.close(); load() }
  catch { confirmRef.value.close() }
}

async function markPaid(si: SupplierInvoice) {
  try {
    await api.patch(`/supplier-invoices/${si.id}`, {
      status: 'paid',
      paid_at: new Date().toISOString(),
    })
    load()
  } catch {}
}
</script>
