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
      <v-btn v-if="quote && TRANSITIONS[quote.status].length" variant="outlined" @click="statusDialog = true">Status</v-btn>
      <v-btn v-if="quote" variant="outlined" prepend-icon="mdi-eye-outline" @click="openPreview">Vorschau</v-btn>
      <v-btn v-if="quote" variant="outlined" prepend-icon="mdi-file-pdf-box" :loading="pdfLoading" @click="downloadPdf">PDF</v-btn>
      <v-btn color="primary" :loading="saving" @click="save">{{ isNew ? 'Erstellen' : 'Speichern' }}</v-btn>
    </div>
    <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-4">{{ error }}</v-alert>

    <v-row>
      <!-- Header + Verlauf -->
      <v-col cols="12" md="3">
        <v-card class="pa-4 mb-4">
          <div class="text-subtitle-2 mb-3">Angebots-Header</div>
          <v-form ref="formRef">
            <v-autocomplete v-model="form.customer_id" :items="customers" item-title="name" item-value="id"
              label="Kunde *" :rules="[required]" variant="outlined" density="compact" class="mb-2" />
            <v-text-field v-model="form.date" type="date" label="Datum *" :rules="[required]" variant="outlined" density="compact" class="mb-2" />
            <v-text-field v-model="form.valid_until" type="date" label="Gültig bis" variant="outlined" density="compact" class="mb-2" />
            <v-textarea v-model="form.notes" label="Hinweise (Kunde)" rows="2" variant="outlined" density="compact" class="mb-2" />
            <v-textarea v-model="form.internal_notes" label="Interne Notizen" rows="2" variant="outlined" density="compact" />
          </v-form>
        </v-card>

        <!-- KI-Assistent -->
        <v-card class="pa-4 mb-4">
          <div class="text-subtitle-2 mb-2 d-flex align-center">
            <v-icon size="small" color="purple" class="mr-1">mdi-brain</v-icon>
            KI-Assistent
          </div>
          <v-textarea v-model="llmKeywords" label="Stichwörter / Freitext" rows="2"
            variant="outlined" density="compact" class="mb-2" hint="z.B. 'Fliesenarbeiten Bad 12m²'" />
          <div class="d-flex gap-2">
            <v-btn size="small" color="purple" variant="tonal" :loading="llmLoading" @click="llmSuggest">
              Position
            </v-btn>
            <v-btn size="small" color="purple" variant="tonal" :loading="llmLoading" @click="llmSplit">
              Aufteilen
            </v-btn>
          </div>
          <v-alert v-if="llmError" type="warning" variant="tonal" density="compact" class="mt-2">{{ llmError }}</v-alert>
        </v-card>

        <!-- Positionsverlauf -->
        <v-card class="pa-4">
          <div class="text-subtitle-2 mb-2 d-flex align-center">
            Positionsverlauf
            <v-btn size="x-small" icon variant="text" class="ml-1" @click="loadHistory"><v-icon>mdi-refresh</v-icon></v-btn>
          </div>
          <v-text-field v-model="historySearch" label="Suchen" prepend-inner-icon="mdi-magnify"
            variant="outlined" density="compact" clearable class="mb-2" @update:model-value="onHistorySearch" />
          <v-list density="compact" max-height="250" style="overflow-y:auto">
            <v-list-item v-for="h in history" :key="h.id" :title="h.description"
              :subtitle="`${h.unit_price}€/${h.unit} · ${h.vat_rate}% · ${h.usage_count}×`"
              class="px-0" style="cursor:pointer" @click="addItemFromHistory(h, activeGroupIdx)">
              <template #append><v-icon size="small" color="primary">mdi-plus-circle</v-icon></template>
            </v-list-item>
            <v-list-item v-if="!history.length" class="px-0">
              <v-list-item-title class="text-caption text-medium-emphasis">Keine Einträge</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <!-- Gruppen + Positionen -->
      <v-col cols="12" md="9">

        <!-- Ungrouped items (shown first if any, or when no groups) -->
        <v-card class="mb-3">
          <v-card-title class="d-flex align-center py-2 px-4">
            <span class="text-subtitle-1">Allgemeine Positionen</span>
            <v-spacer />
            <v-btn size="small" variant="tonal" color="primary" prepend-icon="mdi-plus"
              @click="addItemToGroup(-1)">Position</v-btn>
            <v-btn size="small" variant="tonal" color="indigo" prepend-icon="mdi-clock-outline"
              class="ml-1" @click="addHoursToGroup(-1)">Stunden</v-btn>
            <v-btn size="small" variant="tonal" color="secondary" prepend-icon="mdi-package-variant"
              class="ml-1" @click="openMaterialPicker(-1)">Aus Stamm</v-btn>
          </v-card-title>
          <ItemsTable :items="form.items" @remove="removeItemFromGroup(-1, $event)"
            @update="updateItem('root', $event.idx, $event.field, $event.value)" />
          <div v-if="form.items.length" class="pa-3 d-flex justify-end">
            <GroupSubtotal :items="form.items" />
          </div>
        </v-card>

        <!-- Groups -->
        <v-card v-for="(grp, gi) in form.groups" :key="gi" class="mb-3" :class="activeGroupIdx === gi ? 'border-primary' : ''"
          @click="activeGroupIdx = gi">
          <v-card-title class="d-flex align-center py-2 px-4">
            <v-icon class="mr-2" color="primary">mdi-folder-outline</v-icon>
            <v-text-field v-model="grp.title" variant="plain" density="compact" hide-details
              placeholder="Gruppenbezeichnung…" style="max-width:220px" @click.stop />
            <v-spacer />
            <v-btn size="small" variant="tonal" color="primary" prepend-icon="mdi-plus"
              @click.stop="addItemToGroup(gi)">Position</v-btn>
            <v-btn size="small" variant="tonal" color="indigo" prepend-icon="mdi-clock-outline"
              class="ml-1" @click.stop="addHoursToGroup(gi)">Stunden</v-btn>
            <v-btn size="small" variant="tonal" color="secondary" prepend-icon="mdi-package-variant"
              class="ml-1" @click.stop="openMaterialPicker(gi)">Aus Stamm</v-btn>
            <v-btn size="small" icon variant="text" color="error" class="ml-1"
              @click.stop="removeGroup(gi)"><v-icon>mdi-delete</v-icon></v-btn>
          </v-card-title>
          <ItemsTable :items="grp.items" @remove="removeItemFromGroup(gi, $event)"
            @update="updateItem(gi, $event.idx, $event.field, $event.value)" />
          <div class="pa-3 d-flex justify-end">
            <GroupSubtotal :items="grp.items" />
          </div>
        </v-card>

        <!-- Add group -->
        <v-btn variant="outlined" prepend-icon="mdi-folder-plus" class="mb-3" @click="addGroup">
          Gruppe hinzufügen
        </v-btn>

        <!-- Global totals -->
        <v-card class="pa-4">
          <div class="d-flex justify-end">
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

    <!-- Vorschau Dialog -->
    <v-dialog v-model="previewDialog" max-width="900" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center">
          Vorschau — {{ quote?.quote_no }}
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
          <v-alert v-if="quote?.paperless_doc_id" type="success" variant="tonal" density="compact" class="text-caption flex-grow-1">
            In Paperless gespeichert (ID {{ quote.paperless_doc_id }})
          </v-alert>
          <v-spacer />
          <v-btn variant="text" @click="previewDialog = false">Schließen</v-btn>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-file-pdf-box" :loading="pdfLoading" @click="downloadPdf">PDF herunterladen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Status Dialog -->
    <v-dialog v-model="statusDialog" max-width="360">
      <v-card>
        <v-card-title>Status ändern</v-card-title>
        <v-card-text>
          <div class="d-flex gap-2 flex-wrap">
            <v-btn v-for="s in (quote ? TRANSITIONS[quote.status] : [])" :key="s"
              :color="STATUS_COLORS[s]" variant="flat" size="small" @click="applyStatus(s)">
              {{ STATUS_LABELS[s] }}
            </v-btn>
          </div>
        </v-card-text>
        <v-card-actions><v-spacer /><v-btn variant="text" @click="statusDialog = false">Schließen</v-btn></v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Material Picker -->
    <v-dialog v-model="materialDialog" max-width="640">
      <v-card>
        <v-card-title>Artikel aus Materialstamm wählen</v-card-title>
        <v-card-text>
          <v-text-field v-model="materialSearch" label="Suchen" prepend-inner-icon="mdi-magnify"
            variant="outlined" density="compact" class="mb-2" @update:model-value="searchMaterials" />
          <v-table density="compact" style="max-height:340px; overflow-y:auto">
            <thead><tr><th>Bezeichnung</th><th>Einh.</th><th class="text-right">VK €</th><th class="text-right">MwSt.</th><th></th></tr></thead>
            <tbody>
              <tr v-if="!materialList.length"><td colspan="5" class="text-center pa-3 text-medium-emphasis">Keine Artikel</td></tr>
              <tr v-for="m in materialList" :key="m.id" style="cursor:pointer" @click="selectMaterial(m)">
                <td>{{ m.name }}<div v-if="m.sku" class="text-caption text-medium-emphasis">{{ m.sku }}</div></td>
                <td>{{ m.unit }}</td>
                <td class="text-right">{{ m.sale_price ?? '—' }}</td>
                <td class="text-right">{{ m.vat_rate }}%</td>
                <td><v-btn icon size="x-small" variant="text" color="primary"><v-icon>mdi-plus</v-icon></v-btn></td>
              </tr>
            </tbody>
          </v-table>
        </v-card-text>
        <v-card-actions><v-spacer /><v-btn variant="text" @click="materialDialog = false">Schließen</v-btn></v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  quotesApi, type Quote, type QuoteItemIn, type PositionHistory,
  STATUS_COLORS, STATUS_LABELS, TRANSITIONS, type QuoteStatus,
} from '@/api/quotes'
import { customersApi, type Customer, materialsApi, type Material } from '@/api/stammdaten'
import { api } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const quoteId = computed(() => route.params.id ? Number(route.params.id) : null)
const isNew = computed(() => !quoteId.value)

const quote = ref<Quote | null>(null)
const saving = ref(false)
const pdfLoading = ref(false)
const error = ref('')
const formRef = ref()
const customers = ref<Customer[]>([])
const history = ref<PositionHistory[]>([])
const historySearch = ref('')
const statusDialog = ref(false)
const materialDialog = ref(false)
const materialSearch = ref('')
const materialList = ref<Material[]>([])
const materialTargetGroup = ref<number>(-1)  // -1 = ungrouped
const activeGroupIdx = ref<number>(-1)

interface LocalItem { description: string; qty: string; unit: string; unit_price: string; discount_pct: string; vat_rate: string; material_id: number | null }
interface LocalGroup { title: string; items: LocalItem[] }

const today = new Date().toISOString().slice(0, 10)
const form = ref<{
  customer_id: number | null; date: string; valid_until: string;
  notes: string; internal_notes: string; groups: LocalGroup[]; items: LocalItem[]
}>({ customer_id: null, date: today, valid_until: '', notes: '', internal_notes: '', groups: [], items: [] })

const required = (v: unknown) => !!v || 'Pflichtfeld'

// ── Totals ──────────────────────────────────────────────────────────────────
function lineTotal(item: LocalItem): number {
  const qty = parseFloat(item.qty) || 0
  const price = parseFloat(item.unit_price) || 0
  const disc = parseFloat(item.discount_pct) || 0
  return Math.round(qty * price * (1 - disc / 100) * 100) / 100
}

const totals = computed(() => {
  let subtotal = 0; let vatTotal = 0
  const allItems = [...form.value.items, ...form.value.groups.flatMap(g => g.items)]
  for (const item of allItems) {
    const lt = lineTotal(item)
    subtotal += lt
    vatTotal += Math.round(lt * (parseFloat(item.vat_rate) || 0) / 100 * 100) / 100
  }
  return { subtotal: Math.round(subtotal * 100) / 100, vatTotal: Math.round(vatTotal * 100) / 100, total: Math.round((subtotal + vatTotal) * 100) / 100 }
})

// ── Items + Groups ──────────────────────────────────────────────────────────
function addGroup() { form.value.groups.push({ title: `Gruppe ${form.value.groups.length + 1}`, items: [] }) }
function removeGroup(gi: number) { form.value.groups.splice(gi, 1) }

function emptyItem(): LocalItem {
  return { description: '', qty: '1', unit: 'Stk', unit_price: '0.00', discount_pct: '0.00', vat_rate: '19.00', material_id: null }
}
function emptyHoursItem(): LocalItem {
  return { description: 'Arbeitszeit', qty: '1.000', unit: 'h', unit_price: '0.00', discount_pct: '0.00', vat_rate: '19.00', material_id: null }
}
function addItemToGroup(gi: number) {
  if (gi === -1) form.value.items.push(emptyItem())
  else form.value.groups[gi]?.items.push(emptyItem())
}
function addHoursToGroup(gi: number) {
  if (gi === -1) form.value.items.push(emptyHoursItem())
  else form.value.groups[gi]?.items.push(emptyHoursItem())
}
function removeItemFromGroup(gi: number, idx: number) {
  if (gi === -1) form.value.items.splice(idx, 1)
  else form.value.groups[gi]?.items.splice(idx, 1)
}
function updateItem(gi: number | 'root', idx: number, field: string, value: string) {
  const item = gi === 'root' || gi === -1 ? form.value.items[idx] : form.value.groups[gi as number]?.items[idx]
  if (item) (item as Record<string, unknown>)[field] = value
}
function addItemFromHistory(h: PositionHistory, gi: number) {
  const item: LocalItem = { description: h.description, qty: '1', unit: h.unit, unit_price: h.unit_price, discount_pct: '0.00', vat_rate: h.vat_rate, material_id: null }
  if (gi === -1) form.value.items.push(item)
  else if (gi >= 0) form.value.groups[gi]?.items.push(item)
  else form.value.items.push(item)
}

// ── LLM-Assistent ───────────────────────────────────────────────────────────
const llmKeywords = ref('')
const llmLoading = ref(false)
const llmError = ref('')

async function llmSuggest() {
  if (!llmKeywords.value.trim()) return
  llmLoading.value = true; llmError.value = ''
  try {
    const res = await api.post<{ description: string; unit: string; unit_price?: string; vat_rate?: string }>(
      '/llm/suggest-position',
      { keywords: llmKeywords.value, context: 'bau' },
    )
    const item: LocalItem = {
      description: res.description,
      qty: '1',
      unit: res.unit ?? 'Stk',
      unit_price: res.unit_price ?? '0.00',
      discount_pct: '0.00',
      vat_rate: res.vat_rate ?? '19.00',
      material_id: null,
    }
    if (activeGroupIdx.value === -1) form.value.items.push(item)
    else form.value.groups[activeGroupIdx.value]?.items.push(item)
    llmKeywords.value = ''
  } catch {
    llmError.value = 'KI nicht verfügbar — Ollama läuft?'
  } finally { llmLoading.value = false }
}

async function llmSplit() {
  if (!llmKeywords.value.trim()) return
  llmLoading.value = true; llmError.value = ''
  try {
    const items = await api.post<Array<{ description: string; qty: string; unit: string; unit_price: string; vat_rate: string }>>(
      '/llm/split-positions',
      { text: llmKeywords.value, context: 'bau' },
    )
    for (const r of items) {
      const item: LocalItem = {
        description: r.description,
        qty: r.qty ?? '1',
        unit: r.unit ?? 'Stk',
        unit_price: r.unit_price ?? '0.00',
        discount_pct: '0.00',
        vat_rate: r.vat_rate ?? '19.00',
        material_id: null,
      }
      if (activeGroupIdx.value === -1) form.value.items.push(item)
      else form.value.groups[activeGroupIdx.value]?.items.push(item)
    }
    llmKeywords.value = ''
  } catch {
    llmError.value = 'KI nicht verfügbar — Ollama läuft?'
  } finally { llmLoading.value = false }
}

// ── Material Picker ─────────────────────────────────────────────────────────
async function openMaterialPicker(gi: number) {
  materialTargetGroup.value = gi
  materialSearch.value = ''
  materialDialog.value = true
  const res = await materialsApi.list({ limit: 100, active_only: true })
  materialList.value = res.items
}
let mt: ReturnType<typeof setTimeout>
async function searchMaterials() {
  clearTimeout(mt); mt = setTimeout(async () => {
    const res = await materialsApi.list({ search: materialSearch.value || undefined, limit: 100, active_only: true })
    materialList.value = res.items
  }, 300)
}
function selectMaterial(m: Material) {
  const item: LocalItem = {
    description: m.name + (m.description ? ` — ${m.description}` : ''),
    qty: '1', unit: m.unit,
    unit_price: m.sale_price ?? '0.00',
    discount_pct: '0.00',
    vat_rate: m.vat_rate,
    material_id: m.id,
  }
  const gi = materialTargetGroup.value
  if (gi === -1) form.value.items.push(item)
  else form.value.groups[gi]?.items.push(item)
  materialDialog.value = false
}

// ── Load ────────────────────────────────────────────────────────────────────
onMounted(async () => {
  const [custRes] = await Promise.all([
    customersApi.list({ limit: 500 }),
    loadHistory(),
  ])
  customers.value = custRes.items
  if (quoteId.value) await loadQuote()
})

async function loadHistory() {
  history.value = await quotesApi.positionHistory(historySearch.value || undefined)
}
let ht: ReturnType<typeof setTimeout>
function onHistorySearch() { clearTimeout(ht); ht = setTimeout(loadHistory, 300) }

async function loadQuote() {
  if (!quoteId.value) return
  const q = await quotesApi.get(quoteId.value)
  quote.value = q
  form.value = {
    customer_id: q.customer_id,
    date: q.date,                 // Backend returns "date"
    valid_until: q.valid_until ?? '',
    notes: q.notes ?? '',
    internal_notes: q.internal_notes ?? '',
    groups: q.groups.map(g => ({
      title: g.title,
      items: g.items.map(i => ({
        description: i.description, qty: i.qty, unit: i.unit,
        unit_price: i.unit_price, discount_pct: i.discount_pct,
        vat_rate: i.vat_rate, material_id: i.material_id,
      })),
    })),
    items: q.items.map(i => ({
      description: i.description, qty: i.qty, unit: i.unit,
      unit_price: i.unit_price, discount_pct: i.discount_pct,
      vat_rate: i.vat_rate, material_id: i.material_id,
    })),
  }
}

// ── Save ────────────────────────────────────────────────────────────────────
async function save() {
  const { valid } = await formRef.value.validate()
  if (!valid) return
  saving.value = true; error.value = ''
  try {
    const payload = {
      customer_id: form.value.customer_id!,
      quote_date: form.value.date,     // Backend expects "quote_date" for input
      valid_until: form.value.valid_until || null,
      notes: form.value.notes || null,
      internal_notes: form.value.internal_notes || null,
      groups: form.value.groups.map((g, gi) => ({
        title: g.title, position: gi + 1,
        items: g.items.map((item, ii) => toItemIn(item, ii)),
      })),
      items: form.value.items.map((item, ii) => toItemIn(item, ii)),
    }
    if (isNew.value) {
      const created = await quotesApi.create(payload)
      router.replace({ name: 'quote-edit', params: { id: created.id } })
    } else {
      quote.value = await quotesApi.update(quoteId.value!, payload)
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Fehler beim Speichern'
  } finally { saving.value = false }
}

function toItemIn(item: LocalItem, idx: number): QuoteItemIn {
  return {
    description: item.description, qty: item.qty, unit: item.unit,
    unit_price: item.unit_price, discount_pct: item.discount_pct || '0.00',
    vat_rate: item.vat_rate, material_id: item.material_id, position: idx + 1,
  }
}

// ── Vorschau ────────────────────────────────────────────────────────────────
const previewDialog = ref(false)
const previewHtml = ref('')
const previewLoading = ref(false)

async function openPreview() {
  if (!quoteId.value) return
  previewDialog.value = true
  previewLoading.value = true
  previewHtml.value = ''
  try {
    const res = await fetch(`/api/v1/quotes/${quoteId.value}/preview`, {
      headers: {
        Authorization: `Bearer ${auth.accessToken}`,
        ...(auth.currentTenant ? { 'X-Tenant-ID': String(auth.currentTenant.id) } : {}),
      },
    })
    previewHtml.value = await res.text()
  } catch { previewHtml.value = '<p style="padding:20px;color:red">Vorschau nicht verfügbar</p>' }
  finally { previewLoading.value = false }
}

// ── PDF ─────────────────────────────────────────────────────────────────────
async function downloadPdf() {
  if (!quoteId.value) return
  pdfLoading.value = true
  try {
    const res = await fetch(`/api/v1/quotes/${quoteId.value}/pdf`, {
      headers: {
        Authorization: `Bearer ${auth.accessToken}`,
        ...(auth.currentTenant ? { 'X-Tenant-ID': String(auth.currentTenant.id) } : {}),
      },
    })
    if (!res.ok) throw new Error(`${res.status}`)
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${quote.value?.quote_no ?? 'angebot'}.pdf`
    a.click(); URL.revokeObjectURL(a.href)
  } catch (e) { error.value = 'PDF-Download fehlgeschlagen' }
  finally { pdfLoading.value = false }
}

// ── Status ──────────────────────────────────────────────────────────────────
async function applyStatus(s: QuoteStatus) {
  if (!quoteId.value) return
  try { quote.value = await quotesApi.setStatus(quoteId.value, s); statusDialog.value = false }
  catch (e) { error.value = e instanceof Error ? e.message : 'Fehler' }
}
</script>

<!-- ── Child components (inline for single-file) ──────────────────────────── -->
<script lang="ts">
import { defineComponent, h, computed as vueComputed } from 'vue'

// ItemsTable — renders a list of items in a compact table
export const ItemsTable = defineComponent({
  props: { items: { type: Array as () => Array<Record<string, string | number | null>>, default: () => [] } },
  emits: ['remove', 'update'],
  setup(props, { emit }) {
    const lt = (item: Record<string, string | number | null>) => {
      const qty = parseFloat(String(item.qty)) || 0
      const price = parseFloat(String(item.unit_price)) || 0
      const disc = parseFloat(String(item.discount_pct)) || 0
      return (Math.round(qty * price * (1 - disc / 100) * 100) / 100).toFixed(2)
    }
    return () => h('table', { style: 'width:100%;border-collapse:collapse;font-size:0.85rem' }, [
      h('thead', {}, h('tr', {}, [
        h('th', { style: 'width:4%;padding:4px 8px;background:#f5f5f5;text-align:center' }, '#'),
        h('th', { style: 'width:35%;padding:4px 8px;background:#f5f5f5' }, 'Beschreibung'),
        h('th', { style: 'width:9%;padding:4px 8px;background:#f5f5f5' }, 'Menge'),
        h('th', { style: 'width:8%;padding:4px 8px;background:#f5f5f5' }, 'Einh.'),
        h('th', { style: 'width:10%;padding:4px 8px;background:#f5f5f5' }, 'EP €'),
        h('th', { style: 'width:7%;padding:4px 8px;background:#f5f5f5' }, 'Rab%'),
        h('th', { style: 'width:9%;padding:4px 8px;background:#f5f5f5' }, 'MwSt%'),
        h('th', { style: 'width:11%;padding:4px 8px;background:#f5f5f5;text-align:right' }, 'Gesamt €'),
        h('th', { style: 'width:5%;padding:4px 8px;background:#f5f5f5' }, ''),
      ])),
      props.items.length === 0
        ? h('tbody', {}, h('tr', {}, h('td', { colSpan: 9, style: 'text-align:center;padding:12px;color:#999;font-size:0.8rem' }, 'Keine Positionen — Position hinzufügen')))
        : h('tbody', {}, props.items.map((item, idx) =>
          h('tr', { key: idx, style: idx % 2 === 0 ? '' : 'background:#fafafa' }, [
            h('td', { style: 'padding:2px 8px;text-align:center;color:#999' }, String(idx + 1)),
            h('td', { style: 'padding:2px 4px' }, h('input', {
              value: item.description, placeholder: 'Beschreibung…',
              style: 'width:100%;border:none;background:transparent;padding:4px;font-size:0.85rem',
              onInput: (e: Event) => emit('update', { idx, field: 'description', value: (e.target as HTMLInputElement).value }),
            })),
            h('td', { style: 'padding:2px 4px' }, h('input', {
              value: item.qty, type: 'number', step: '0.001',
              style: 'width:100%;border:none;background:transparent;padding:4px;font-size:0.85rem;text-align:right',
              onInput: (e: Event) => emit('update', { idx, field: 'qty', value: (e.target as HTMLInputElement).value }),
            })),
            h('td', { style: 'padding:2px 4px' }, h('input', {
              value: item.unit,
              style: 'width:100%;border:none;background:transparent;padding:4px;font-size:0.85rem',
              onInput: (e: Event) => emit('update', { idx, field: 'unit', value: (e.target as HTMLInputElement).value }),
            })),
            h('td', { style: 'padding:2px 4px' }, h('input', {
              value: item.unit_price, type: 'number', step: '0.01',
              style: 'width:100%;border:none;background:transparent;padding:4px;font-size:0.85rem;text-align:right',
              onInput: (e: Event) => emit('update', { idx, field: 'unit_price', value: (e.target as HTMLInputElement).value }),
            })),
            h('td', { style: 'padding:2px 4px' }, h('input', {
              value: item.discount_pct, type: 'number', step: '0.1',
              style: 'width:100%;border:none;background:transparent;padding:4px;font-size:0.85rem;text-align:right',
              onInput: (e: Event) => emit('update', { idx, field: 'discount_pct', value: (e.target as HTMLInputElement).value }),
            })),
            h('td', { style: 'padding:2px 4px' }, h('select', {
              value: item.vat_rate,
              style: 'width:100%;border:none;background:transparent;padding:4px;font-size:0.85rem',
              onChange: (e: Event) => emit('update', { idx, field: 'vat_rate', value: (e.target as HTMLSelectElement).value }),
            }, ['0.00', '7.00', '19.00'].map(v => h('option', { value: v, selected: String(item.vat_rate) === v }, v + '%')))),
            h('td', { style: 'padding:2px 8px;text-align:right;font-weight:600' }, lt(item)),
            h('td', { style: 'padding:2px 4px;text-align:center' }, h('button', {
              style: 'border:none;background:none;cursor:pointer;color:#f44336;font-size:1.1rem',
              onClick: () => emit('remove', idx),
            }, '×')),
          ])
        )),
    ])
  },
})

// GroupSubtotal
export const GroupSubtotal = defineComponent({
  props: { items: { type: Array as () => Array<Record<string, string | number | null>>, default: () => [] } },
  setup(props) {
    const calc = vueComputed(() => {
      let sub = 0; let vat = 0
      for (const item of props.items) {
        const qty = parseFloat(String(item.qty)) || 0
        const price = parseFloat(String(item.unit_price)) || 0
        const disc = parseFloat(String(item.discount_pct)) || 0
        const vatRate = parseFloat(String(item.vat_rate)) || 0
        const lt = Math.round(qty * price * (1 - disc / 100) * 100) / 100
        sub += lt
        vat += Math.round(lt * vatRate / 100 * 100) / 100
      }
      return { sub: sub.toFixed(2), vat: vat.toFixed(2), total: (sub + vat).toFixed(2) }
    })
    return () => h('div', { style: 'font-size:0.85rem;color:#555;display:flex;gap:16px' }, [
      h('span', {}, `Netto: ${calc.value.sub} €`),
      h('span', {}, `MwSt: ${calc.value.vat} €`),
      h('strong', {}, `Gesamt: ${calc.value.total} €`),
    ])
  },
})
</script>
