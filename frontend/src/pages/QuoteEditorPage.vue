<template>
  <div>
    <!-- Toolbar -->
    <div class="d-flex align-center mb-4 gap-2 flex-wrap">
      <v-btn variant="text" prepend-icon="mdi-arrow-left" :to="{ name: 'quotes' }">Angebote</v-btn>
      <h1 class="text-h5 flex-grow-1">
        {{ isNew ? 'Neues Angebot' : quote?.quote_no }}
        <v-chip v-if="quote" :color="STATUS_COLORS[quote.status]" size="small" label class="ml-2">
          {{ STATUS_LABELS[quote.status] }}
        </v-chip>
      </h1>
      <v-btn v-if="quote && TRANSITIONS[quote.status].length" variant="outlined" @click="statusDialog = true">
        Status ändern
      </v-btn>
      <v-btn v-if="quote" variant="outlined" prepend-icon="mdi-file-pdf-box" :loading="pdfLoading" @click="downloadPdf">
        PDF
      </v-btn>
      <v-btn color="primary" :loading="saving" @click="save">
        {{ isNew ? 'Erstellen' : 'Speichern' }}
      </v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-4">{{ error }}</v-alert>

    <v-row>
      <!-- Left: Header form -->
      <v-col cols="12" md="4">
        <v-card class="pa-4">
          <v-card-title class="px-0 pt-0 text-subtitle-1">Angebots-Header</v-card-title>
          <v-form ref="formRef">
            <v-autocomplete
              v-model="form.customer_id" :items="customers" item-title="name" item-value="id"
              label="Kunde *" :rules="[required]" variant="outlined" density="compact" class="mb-2"
              :loading="customersLoading"
            />
            <v-text-field v-model="form.date" label="Datum *" type="date" :rules="[required]" variant="outlined" density="compact" class="mb-2" />
            <v-text-field v-model="form.valid_until" label="Gültig bis" type="date" variant="outlined" density="compact" class="mb-2" />
            <v-textarea v-model="form.notes" label="Hinweise (für Kunden)" rows="3" variant="outlined" density="compact" class="mb-2" />
            <v-textarea v-model="form.internal_notes" label="Interne Notizen" rows="2" variant="outlined" density="compact" />
          </v-form>
        </v-card>

        <!-- Position History -->
        <v-card class="pa-4 mt-4">
          <v-card-title class="px-0 pt-0 text-subtitle-1">
            Letzte Positionen
            <v-btn size="x-small" variant="text" icon class="ml-1" @click="loadHistory">
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
          </v-card-title>
          <v-text-field
            v-model="historySearch" label="Suchen" prepend-inner-icon="mdi-magnify"
            variant="outlined" density="compact" clearable class="mb-2"
            @update:model-value="onHistorySearch"
          />
          <v-list density="compact" max-height="280" style="overflow-y:auto">
            <v-list-item
              v-for="h in history" :key="h.id"
              :title="h.description"
              :subtitle="`${h.unit_price} € / ${h.unit} · ${h.vat_rate}% · ${h.usage_count}×`"
              class="px-0" style="cursor:pointer"
              @click="addFromHistory(h)"
            >
              <template #append>
                <v-icon size="small" color="primary">mdi-plus-circle</v-icon>
              </template>
            </v-list-item>
            <v-list-item v-if="!history.length" class="px-0">
              <v-list-item-title class="text-medium-emphasis text-caption">Noch keine Positionen gespeichert</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <!-- Right: Items + Totals -->
      <v-col cols="12" md="8">
        <v-card>
          <v-card-title class="d-flex align-center">
            Positionen
            <v-spacer />
            <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-plus" @click="addItem">
              Position
            </v-btn>
          </v-card-title>

          <v-table density="compact">
            <thead>
              <tr>
                <th style="width:4%">Pos.</th>
                <th style="width:32%">Beschreibung *</th>
                <th style="width:9%">Menge</th>
                <th style="width:8%">Einh.</th>
                <th style="width:10%">EP (€)</th>
                <th style="width:7%">Rab.%</th>
                <th style="width:9%">MwSt.%</th>
                <th style="width:11%" class="text-right">Gesamt €</th>
                <th style="width:6%"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!form.items.length">
                <td colspan="9" class="text-center pa-4 text-medium-emphasis">
                  Noch keine Positionen — „Position" klicken oder aus Verlauf wählen
                </td>
              </tr>
              <tr v-for="(item, idx) in form.items" :key="idx">
                <td class="text-center">{{ idx + 1 }}</td>
                <td>
                  <v-text-field
                    v-model="item.description" placeholder="Freitext…" variant="plain"
                    density="compact" hide-details single-line @update:model-value="recalc"
                  />
                </td>
                <td>
                  <v-text-field
                    v-model="item.qty" type="number" step="0.001" min="0" variant="plain"
                    density="compact" hide-details single-line @update:model-value="recalc"
                  />
                </td>
                <td>
                  <v-text-field
                    v-model="item.unit" variant="plain" density="compact" hide-details single-line
                  />
                </td>
                <td>
                  <v-text-field
                    v-model="item.unit_price" type="number" step="0.01" min="0" variant="plain"
                    density="compact" hide-details single-line @update:model-value="recalc"
                  />
                </td>
                <td>
                  <v-text-field
                    v-model="item.discount_pct" type="number" step="0.1" min="0" max="100"
                    variant="plain" density="compact" hide-details single-line @update:model-value="recalc"
                  />
                </td>
                <td>
                  <v-select
                    v-model="item.vat_rate" :items="vatOptions" variant="plain"
                    density="compact" hide-details @update:model-value="recalc"
                  />
                </td>
                <td class="text-right pr-2">
                  <strong>{{ lineTotal(item).toFixed(2) }}</strong>
                </td>
                <td>
                  <v-btn icon size="x-small" variant="text" color="error" @click="removeItem(idx)">
                    <v-icon>mdi-close</v-icon>
                  </v-btn>
                </td>
              </tr>
            </tbody>
          </v-table>

          <!-- Totals -->
          <div class="d-flex justify-end pa-4">
            <v-table density="compact" style="min-width:280px">
              <tbody>
                <tr><td class="text-medium-emphasis">Netto</td><td class="text-right"><strong>{{ totals.subtotal.toFixed(2) }} €</strong></td></tr>
                <tr><td class="text-medium-emphasis">MwSt.</td><td class="text-right"><strong>{{ totals.vatTotal.toFixed(2) }} €</strong></td></tr>
                <tr style="font-size:1.1em">
                  <td><strong>Gesamt</strong></td>
                  <td class="text-right"><strong>{{ totals.total.toFixed(2) }} €</strong></td>
                </tr>
              </tbody>
            </v-table>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Status Dialog -->
    <v-dialog v-model="statusDialog" max-width="360">
      <v-card>
        <v-card-title>Status ändern</v-card-title>
        <v-card-text>
          <v-btn-toggle v-model="newStatus" mandatory color="primary" class="flex-wrap">
            <v-btn
              v-for="s in (quote ? TRANSITIONS[quote.status] : [])" :key="s" :value="s" size="small"
            >{{ STATUS_LABELS[s] }}</v-btn>
          </v-btn-toggle>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="statusDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" variant="flat" :disabled="!newStatus" @click="applyStatus">Übernehmen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { quotesApi, type Quote, type QuoteItemIn, type PositionHistory, STATUS_COLORS, STATUS_LABELS, TRANSITIONS, type QuoteStatus } from '@/api/quotes'
import { customersApi, type Customer } from '@/api/stammdaten'

const route = useRoute()
const router = useRouter()

const quoteId = computed(() => route.params.id ? Number(route.params.id) : null)
const isNew = computed(() => !quoteId.value)

const quote = ref<Quote | null>(null)
const saving = ref(false)
const pdfLoading = ref(false)
const error = ref('')
const formRef = ref()
const customers = ref<Customer[]>([])
const customersLoading = ref(false)
const history = ref<PositionHistory[]>([])
const historySearch = ref('')
const statusDialog = ref(false)
const newStatus = ref<QuoteStatus | null>(null)

const vatOptions = ['0.00', '7.00', '19.00']

interface LocalItem {
  description: string
  qty: string
  unit: string
  unit_price: string
  discount_pct: string
  vat_rate: string
  material_id: number | null
}

interface FormState {
  customer_id: number | null
  date: string
  valid_until: string
  notes: string
  internal_notes: string
  items: LocalItem[]
}

const today = new Date().toISOString().slice(0, 10)
const form = ref<FormState>({
  customer_id: null, date: today, valid_until: '', notes: '', internal_notes: '', items: [],
})

const required = (v: unknown) => !!v || 'Pflichtfeld'

// ── Totals (local preview) ──────────────────────────────────────────────────
function lineTotal(item: LocalItem): number {
  const qty = parseFloat(item.qty) || 0
  const price = parseFloat(item.unit_price) || 0
  const disc = parseFloat(item.discount_pct) || 0
  return Math.round(qty * price * (1 - disc / 100) * 100) / 100
}

const totals = computed(() => {
  let subtotal = 0
  let vatTotal = 0
  for (const item of form.value.items) {
    const lt = lineTotal(item)
    subtotal += lt
    vatTotal += Math.round(lt * (parseFloat(item.vat_rate) || 0) / 100 * 100) / 100
  }
  return { subtotal: Math.round(subtotal * 100) / 100, vatTotal: Math.round(vatTotal * 100) / 100, total: Math.round((subtotal + vatTotal) * 100) / 100 }
})

function recalc() { /* reactive, computed handles it */ }

// ── Items ───────────────────────────────────────────────────────────────────
function addItem() {
  form.value.items.push({ description: '', qty: '1', unit: 'Stk', unit_price: '0.00', discount_pct: '0.00', vat_rate: '19.00', material_id: null })
}
function removeItem(idx: number) { form.value.items.splice(idx, 1) }

function addFromHistory(h: PositionHistory) {
  form.value.items.push({
    description: h.description, qty: '1', unit: h.unit,
    unit_price: h.unit_price, discount_pct: '0.00', vat_rate: h.vat_rate, material_id: null,
  })
}

// ── Load data ───────────────────────────────────────────────────────────────
async function loadCustomers() {
  customersLoading.value = true
  try {
    const res = await customersApi.list({ limit: 500 })
    customers.value = res.items
  } finally { customersLoading.value = false }
}

async function loadHistory() {
  const res = await quotesApi.positionHistory(historySearch.value || undefined)
  history.value = res
}

let ht: ReturnType<typeof setTimeout>
function onHistorySearch() { clearTimeout(ht); ht = setTimeout(loadHistory, 300) }

async function loadQuote() {
  if (!quoteId.value) return
  const q = await quotesApi.get(quoteId.value)
  quote.value = q
  form.value = {
    customer_id: q.customer_id,
    date: q.quote_date,
    valid_until: q.valid_until ?? '',
    notes: q.notes ?? '',
    internal_notes: q.internal_notes ?? '',
    items: q.items.map(i => ({
      description: i.description, qty: i.qty, unit: i.unit,
      unit_price: i.unit_price, discount_pct: i.discount_pct,
      vat_rate: i.vat_rate, material_id: i.material_id,
    })),
  }
}

onMounted(async () => {
  await Promise.all([loadCustomers(), loadHistory()])
  await loadQuote()
})

// ── Save ────────────────────────────────────────────────────────────────────
async function save() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  saving.value = true
  error.value = ''
  try {
    const payload = {
      customer_id: form.value.customer_id!,
      quote_date: form.value.date,
      valid_until: form.value.valid_until || null,
      notes: form.value.notes || null,
      internal_notes: form.value.internal_notes || null,
      items: form.value.items.map((item, idx) => ({
        description: item.description,
        qty: item.qty,
        unit: item.unit,
        unit_price: item.unit_price,
        discount_pct: item.discount_pct || '0.00',
        vat_rate: item.vat_rate,
        material_id: item.material_id,
        position: idx + 1,
      } satisfies QuoteItemIn)),
    }
    if (isNew.value) {
      const created = await quotesApi.create(payload)
      router.replace({ name: 'quote-edit', params: { id: created.id } })
    } else {
      const updated = await quotesApi.update(quoteId.value!, payload)
      quote.value = updated
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Fehler beim Speichern'
  } finally {
    saving.value = false
  }
}

// ── PDF ─────────────────────────────────────────────────────────────────────
async function downloadPdf() {
  if (!quoteId.value) return
  pdfLoading.value = true
  try {
    window.open(`/api/v1${quotesApi.pdfUrl(quoteId.value).replace('/api/v1', '')}`, '_blank')
  } finally {
    pdfLoading.value = false
  }
}

// ── Status ──────────────────────────────────────────────────────────────────
async function applyStatus() {
  if (!quoteId.value || !newStatus.value) return
  try {
    quote.value = await quotesApi.setStatus(quoteId.value, newStatus.value)
    statusDialog.value = false
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Fehler'
  }
}
</script>
