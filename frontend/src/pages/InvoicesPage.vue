<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h5 flex-grow-1">Rechnungen</h1>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreate">Neue Rechnung</v-btn>
    </div>

    <div class="d-flex gap-2 mb-4 flex-wrap">
      <v-text-field v-model="search" prepend-inner-icon="mdi-magnify" label="Rechnungsnr. oder Kunde" clearable variant="outlined" density="compact" style="max-width:300px" @update:model-value="onSearch" />
      <v-select v-model="statusFilter" :items="statusOptions" label="Status" variant="outlined" density="compact" clearable style="max-width:200px" @update:model-value="() => { page = 1; load() }" />
    </div>

    <v-card>
      <v-table>
        <thead>
          <tr>
            <th>Rechnungsnr.</th>
            <th>Kunde</th>
            <th>Art</th>
            <th>Datum</th>
            <th>Fällig</th>
            <th>Status</th>
            <th class="text-right">Gesamt</th>
            <th class="text-right">Offen</th>
            <th class="text-right">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="9" class="text-center pa-4"><v-progress-circular indeterminate size="24" /></td></tr>
          <tr v-else-if="!items.length"><td colspan="9" class="text-center pa-4 text-medium-emphasis">Keine Rechnungen</td></tr>
          <tr v-for="inv in items" :key="inv.id">
            <td><strong>{{ inv.invoice_no }}</strong></td>
            <td class="text-caption">{{ customerName(inv.customer_id) }}</td>
            <td>{{ KIND_LABELS[inv.kind as InvoiceKind] }}</td>
            <td>{{ fmtDate(inv.invoice_date) }}</td>
            <td :class="isOverdue(inv) ? 'text-error' : ''">{{ inv.due_date ? fmtDate(inv.due_date) : '—' }}</td>
            <td><v-chip :color="STATUS_COLORS[inv.status as InvoiceStatus]" size="small" label>{{ STATUS_LABELS[inv.status as InvoiceStatus] }}</v-chip></td>
            <td class="text-right">{{ fmtEur(inv.total) }}</td>
            <td class="text-right" :class="openAmount(inv) > 0 && inv.status !== 'paid' ? 'text-warning font-weight-bold' : ''">{{ fmtEur(openAmount(inv)) }}</td>
            <td class="text-right">
              <v-btn icon size="small" variant="text" title="Vorschau" @click="openPreview(inv)"><v-icon>mdi-eye-outline</v-icon></v-btn>
              <v-btn icon size="small" variant="text" title="PDF herunterladen" @click="downloadPdf(inv)"><v-icon>mdi-file-pdf-box</v-icon></v-btn>
              <v-btn icon size="small" variant="text" @click="openPayment(inv)" title="Zahlung buchen"><v-icon>mdi-cash-check</v-icon></v-btn>
              <v-btn v-if="TRANSITIONS[inv.status as InvoiceStatus]?.length" icon size="small" variant="text" title="Status ändern" @click="openStatus(inv)"><v-icon>mdi-state-machine</v-icon></v-btn>
              <v-btn v-if="inv.status === 'draft'" icon size="small" variant="text" color="error" @click="askDelete(inv)"><v-icon>mdi-delete</v-icon></v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
      <div class="d-flex align-center justify-space-between pa-3">
        <span class="text-caption text-medium-emphasis">{{ total }} Rechnungen</span>
        <div class="d-flex align-center">
          <v-btn size="small" variant="text" :disabled="page === 1" @click="page--"><v-icon>mdi-chevron-left</v-icon></v-btn>
          <span class="text-caption">{{ page }} / {{ totalPages }}</span>
          <v-btn size="small" variant="text" :disabled="page >= totalPages" @click="page++"><v-icon>mdi-chevron-right</v-icon></v-btn>
        </div>
      </div>
    </v-card>

    <!-- Create Dialog -->
    <v-dialog v-model="createDialog" max-width="600" persistent>
      <v-card>
        <v-card-title>Neue Rechnung</v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-row dense>
              <v-col cols="12" sm="6">
                <v-autocomplete v-model="form.customer_id" :items="customers" item-title="name" item-value="id" label="Kunde *" :rules="[required]" variant="outlined" density="compact" :loading="customersLoading" />
              </v-col>
              <v-col cols="12" sm="6">
                <v-select v-model="form.kind" :items="kindOptions" label="Art" variant="outlined" density="compact" />
              </v-col>
              <v-col cols="12" sm="6"><v-text-field v-model="form.invoice_date" type="date" label="Rechnungsdatum *" :rules="[required]" variant="outlined" density="compact" /></v-col>
              <v-col cols="12" sm="6"><v-text-field v-model="form.due_date" type="date" label="Fällig bis" variant="outlined" density="compact" /></v-col>
              <v-col cols="12"><v-textarea v-model="form.notes" label="Hinweise" rows="2" variant="outlined" density="compact" /></v-col>
            </v-row>
          </v-form>
          <v-alert v-if="formError" type="error" variant="tonal" density="compact" class="mt-2">{{ formError }}</v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="createDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" variant="flat" :loading="saving" @click="saveNew">Erstellen (Entwurf)</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Payment Dialog -->
    <v-dialog v-model="paymentDialog" max-width="480">
      <v-card v-if="paymentTarget">
        <v-card-title>Zahlung buchen — {{ paymentTarget.invoice_no }}</v-card-title>
        <v-card-subtitle>Offen: {{ fmtEur(openAmount(paymentTarget)) }}</v-card-subtitle>
        <v-card-text>
          <v-row dense>
            <v-col cols="6"><v-text-field v-model="payment.payment_date" type="date" label="Datum" variant="outlined" density="compact" /></v-col>
            <v-col cols="6"><v-text-field v-model="payment.amount" type="number" step="0.01" label="Betrag €" variant="outlined" density="compact" /></v-col>
            <v-col cols="6">
              <v-select v-model="payment.method" :items="methodOptions" label="Zahlungsart" variant="outlined" density="compact" />
            </v-col>
            <v-col cols="6"><v-text-field v-model="payment.bank_ref" label="Bankreferenz" variant="outlined" density="compact" /></v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="paymentDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" variant="flat" :loading="paying" @click="bookPayment">Buchen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Vorschau Dialog -->
    <v-dialog v-model="previewDialog" max-width="900" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          Vorschau — {{ previewTarget?.invoice_no }}
          <v-spacer />
          <v-btn size="small" variant="text" icon @click="previewDialog = false"><v-icon>mdi-close</v-icon></v-btn>
        </v-card-title>
        <v-card-text style="padding:0; height:75vh;">
          <div v-if="previewLoading" class="d-flex justify-center align-center" style="height:100%">
            <v-progress-circular indeterminate />
          </div>
          <iframe v-else :srcdoc="previewHtml" style="width:100%;height:100%;border:none;" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="previewDialog = false">Schließen</v-btn>
          <v-btn v-if="previewTarget" color="primary" variant="flat" prepend-icon="mdi-file-pdf-box" @click="downloadPdf(previewTarget); previewDialog = false">PDF herunterladen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Status Dialog -->
    <v-dialog v-model="statusDialog" max-width="360">
      <v-card v-if="statusTarget">
        <v-card-title>Status ändern — {{ statusTarget.invoice_no }}</v-card-title>
        <v-card-text>
          <div class="d-flex gap-2 flex-wrap">
            <v-btn v-for="s in (TRANSITIONS[statusTarget.status as InvoiceStatus] ?? [])" :key="s"
              :color="STATUS_COLORS[s]" variant="flat" size="small" @click="applyStatus(s)">
              {{ STATUS_LABELS[s] }}
            </v-btn>
          </div>
        </v-card-text>
        <v-card-actions><v-spacer /><v-btn variant="text" @click="statusDialog = false">Schließen</v-btn></v-card-actions>
      </v-card>
    </v-dialog>

    <ConfirmDialog ref="confirmRef" title="Rechnung löschen?" :message="`Rechnung ${deleteTarget?.invoice_no} löschen?`" @confirm="doDelete" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { customersApi, type Customer } from '@/api/stammdaten'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const auth = useAuthStore()

type InvoiceStatus = 'draft' | 'sent' | 'paid' | 'overdue' | 'cancelled'
type InvoiceKind = 'final' | 'partial' | 'advance'

interface Payment { id: number; amount: string; payment_date: string; method: string; bank_ref: string | null; note: string | null; created_at: string; invoice_id: number }
interface Invoice { id: number; invoice_no: string; customer_id: number; order_id: number | null; quote_id: number | null; invoice_date: string; due_date: string | null; kind: string; status: string; subtotal: string; vat_total: string; total: string; paid_amount: string; paid_at: string | null; notes: string | null; internal_notes: string | null; pdf_path: string | null; items: unknown[]; payments: Payment[] }

const STATUS_LABELS: Record<InvoiceStatus, string> = { draft: 'Entwurf', sent: 'Gesendet', paid: 'Bezahlt', overdue: 'Überfällig', cancelled: 'Storniert' }
const STATUS_COLORS: Record<InvoiceStatus, string> = { draft: 'default', sent: 'info', paid: 'success', overdue: 'error', cancelled: 'warning' }
const KIND_LABELS: Record<InvoiceKind, string> = { final: 'Schlussrechnung', partial: 'Teilrechnung', advance: 'Abschlagsrechnung' }
const TRANSITIONS: Record<InvoiceStatus, InvoiceStatus[]> = {
  draft: ['sent'],
  sent: ['paid', 'overdue', 'cancelled'],
  paid: [],
  overdue: ['paid', 'cancelled'],
  cancelled: [],
}

const LIMIT = 25
const items = ref<Invoice[]>([])
const total = ref(0)
const loading = ref(false)
const search = ref('')
const statusFilter = ref<string | null>(null)
const page = ref(1)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / LIMIT)))
const createDialog = ref(false)
const saving = ref(false)
const formError = ref('')
const formRef = ref()
const customers = ref<Customer[]>([])
const customersLoading = ref(false)
const deleteTarget = ref<Invoice | null>(null)
const confirmRef = ref()
const paymentDialog = ref(false)
const paymentTarget = ref<Invoice | null>(null)
const paying = ref(false)
const statusDialog = ref(false)
const statusTarget = ref<Invoice | null>(null)
const previewDialog = ref(false)
const previewTarget = ref<Invoice | null>(null)
const previewHtml = ref('')
const previewLoading = ref(false)

const today = new Date().toISOString().slice(0, 10)
const due = new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10)

const form = ref({ customer_id: null as number | null, kind: 'final', invoice_date: today, due_date: due, notes: '' })
const payment = ref({ payment_date: today, amount: '', method: 'transfer', bank_ref: '' })

const statusOptions = [{ title: 'Entwurf', value: 'draft' }, { title: 'Gesendet', value: 'sent' }, { title: 'Bezahlt', value: 'paid' }, { title: 'Überfällig', value: 'overdue' }, { title: 'Storniert', value: 'cancelled' }]
const kindOptions = [{ title: 'Schlussrechnung', value: 'final' }, { title: 'Teilrechnung', value: 'partial' }, { title: 'Abschlagsrechnung', value: 'advance' }]
const methodOptions = [{ title: 'Überweisung', value: 'transfer' }, { title: 'Bar', value: 'cash' }, { title: 'Karte', value: 'card' }]
const required = (v: unknown) => !!v || 'Pflichtfeld'

const fmtDate = (d: string) => new Date(d).toLocaleDateString('de-DE')
const fmtEur = (v: string | number) => `${Number(v).toFixed(2)} €`
const openAmount = (inv: Invoice) => Math.max(0, Number(inv.total) - Number(inv.paid_amount))
const isOverdue = (inv: Invoice) => inv.due_date && new Date(inv.due_date) < new Date() && inv.status === 'sent'
const customerMap = computed(() => Object.fromEntries(customers.value.map(c => [c.id, c.name])))
const customerName = (id: number) => customerMap.value[id] ?? `K${id}`

async function load() {
  loading.value = true
  try {
    const q = new URLSearchParams()
    if ((page.value - 1) * LIMIT) q.set('skip', String((page.value - 1) * LIMIT))
    q.set('limit', String(LIMIT))
    if (search.value) q.set('search', search.value)
    if (statusFilter.value) q.set('status', statusFilter.value)
    const res = await api.get<{ items: Invoice[]; total: number }>(`/invoices?${q}`)
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

function openCreate() { formError.value = ''; createDialog.value = true }

async function saveNew() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  saving.value = true; formError.value = ''
  try {
    await api.post('/invoices', { customer_id: form.value.customer_id!, kind: form.value.kind, invoice_date: form.value.invoice_date, due_date: form.value.due_date || null, notes: form.value.notes || null, items: [] })
    createDialog.value = false; load()
  } catch (e) { formError.value = e instanceof Error ? e.message : 'Fehler' }
  finally { saving.value = false }
}

function askDelete(inv: Invoice) { deleteTarget.value = inv; confirmRef.value.open() }
async function doDelete() {
  if (!deleteTarget.value) return
  try { await api.delete(`/invoices/${deleteTarget.value.id}`); confirmRef.value.close(); load() }
  catch { confirmRef.value.close() }
}

function openPayment(inv: Invoice) {
  paymentTarget.value = inv
  payment.value = { payment_date: today, amount: String(openAmount(inv).toFixed(2)), method: 'transfer', bank_ref: '' }
  paymentDialog.value = true
}

async function bookPayment() {
  if (!paymentTarget.value || !payment.value.amount) return
  paying.value = true
  try {
    await api.post(`/invoices/${paymentTarget.value.id}/payments`, { ...payment.value, bank_ref: payment.value.bank_ref || null })
    paymentDialog.value = false; load()
  } finally { paying.value = false }
}

function openStatus(inv: Invoice) { statusTarget.value = inv; statusDialog.value = true }

async function openPreview(inv: Invoice) {
  previewTarget.value = inv
  previewDialog.value = true
  previewLoading.value = true
  previewHtml.value = ''
  try {
    const res = await fetch(`/api/v1/invoices/${inv.id}/preview`, {
      headers: {
        Authorization: `Bearer ${auth.accessToken}`,
        ...(auth.currentTenant ? { 'X-Tenant-ID': String(auth.currentTenant.id) } : {}),
      },
    })
    previewHtml.value = await res.text()
  } catch { previewHtml.value = '<p style="padding:20px;color:red">Vorschau nicht verfügbar</p>' }
  finally { previewLoading.value = false }
}
async function applyStatus(s: InvoiceStatus) {
  if (!statusTarget.value) return
  try { await api.patch(`/invoices/${statusTarget.value.id}/status`, { status: s }); statusDialog.value = false; load() }
  catch {}
}

async function downloadPdf(inv: Invoice) {
  const res = await fetch(`/api/v1/invoices/${inv.id}/pdf`, {
    headers: {
      Authorization: `Bearer ${auth.accessToken}`,
      ...(auth.currentTenant ? { 'X-Tenant-ID': String(auth.currentTenant.id) } : {}),
    },
  })
  if (!res.ok) return
  const blob = await res.blob()
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${inv.invoice_no}.pdf`
  a.click(); URL.revokeObjectURL(a.href)
}
</script>
