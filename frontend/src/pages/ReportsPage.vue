<template>
  <div>
    <h1 class="text-h5 mb-4">Auswertungen</h1>

    <v-row>
      <!-- USt-Vorschau -->
      <v-col cols="12" md="6">
        <v-card class="mb-4">
          <v-card-title class="d-flex align-center">
            USt-Vorschau
            <v-spacer />
            <v-btn size="small" icon variant="text" :loading="vatLoading" @click="loadVat"><v-icon>mdi-refresh</v-icon></v-btn>
          </v-card-title>
          <v-card-text>
            <v-row dense class="mb-3">
              <v-col cols="6"><v-text-field v-model="vatFrom" type="date" label="Von" variant="outlined" density="compact" @update:model-value="loadVat" /></v-col>
              <v-col cols="6"><v-text-field v-model="vatTo" type="date" label="Bis" variant="outlined" density="compact" @update:model-value="loadVat" /></v-col>
            </v-row>
            <v-table density="compact" v-if="vatData">
              <tbody>
                <tr>
                  <td class="text-medium-emphasis">Soll-USt (Ausgangsrechnungen)</td>
                  <td class="text-right"><strong>{{ fmtEur(vatData.soll_ust) }}</strong></td>
                </tr>
                <tr>
                  <td class="text-medium-emphasis">Vorsteuer (Eingangsrechnungen)</td>
                  <td class="text-right"><strong class="text-success">− {{ fmtEur(vatData.vorsteuer) }}</strong></td>
                </tr>
                <tr style="border-top:2px solid #ccc">
                  <td><strong>Zahllast</strong></td>
                  <td class="text-right">
                    <strong :class="vatData.zahllast >= 0 ? 'text-error' : 'text-success'">
                      {{ fmtEur(vatData.zahllast) }}
                    </strong>
                  </td>
                </tr>
              </tbody>
            </v-table>
            <div v-if="vatData" class="text-caption text-medium-emphasis mt-2">
              Basierend auf {{ vatData.invoices_count }} Ausgangsrechnungen + {{ vatData.supplier_invoices_count }} Eingangsrechnungen
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Steuerberater-Export -->
      <v-col cols="12" md="6">
        <v-card class="mb-4">
          <v-card-title>Steuerberater-Export</v-card-title>
          <v-card-text>
            <p class="text-body-2 text-medium-emphasis mb-3">
              Zip-Bundle mit Ausgangsrechnungen CSV + Zahlungen CSV + manifest.json
            </p>
            <v-row dense>
              <v-col cols="6"><v-text-field v-model="exportFrom" type="date" label="Von" variant="outlined" density="compact" /></v-col>
              <v-col cols="6"><v-text-field v-model="exportTo" type="date" label="Bis" variant="outlined" density="compact" /></v-col>
              <v-col cols="12">
                <v-btn color="primary" :loading="exporting" prepend-icon="mdi-download" @click="doExport">
                  Export herunterladen
                </v-btn>
              </v-col>
            </v-row>
            <v-alert v-if="exportError" type="error" variant="tonal" density="compact" class="mt-2">{{ exportError }}</v-alert>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- DATEV-Export -->
      <v-col cols="12" md="6">
        <v-card class="mb-4">
          <v-card-title>DATEV-Buchungsjournal</v-card-title>
          <v-card-text>
            <p class="text-body-2 text-medium-emphasis mb-3">
              Vereinfachter Buchungsjournal-Export im DATEV-EXTF-Format für den Steuerberater.
            </p>
            <v-row dense>
              <v-col cols="6"><v-text-field v-model="datevFrom" type="date" label="Von" variant="outlined" density="compact" /></v-col>
              <v-col cols="6"><v-text-field v-model="datevTo" type="date" label="Bis" variant="outlined" density="compact" /></v-col>
              <v-col cols="12">
                <v-btn color="secondary" :loading="datevExporting" prepend-icon="mdi-download" @click="doDatevExport">
                  DATEV herunterladen
                </v-btn>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- EÜR-Vorschau -->
    <v-card class="mb-4">
      <v-card-title class="d-flex align-center">
        EÜR-Vorschau
        <v-tooltip text="Einnahmen-Überschuss-Rechnung nach Zufluss-/Abflussprinzip (vereinfacht)"><template #activator="{ props }"><v-icon v-bind="props" size="small" class="ml-1">mdi-information-outline</v-icon></template></v-tooltip>
        <v-spacer />
        <v-btn size="small" icon variant="text" :loading="eurLoading" @click="loadEur"><v-icon>mdi-refresh</v-icon></v-btn>
      </v-card-title>
      <v-card-text>
        <v-row dense class="mb-3">
          <v-col cols="6"><v-text-field v-model="eurFrom" type="date" label="Von" variant="outlined" density="compact" @update:model-value="loadEur" /></v-col>
          <v-col cols="6"><v-text-field v-model="eurTo" type="date" label="Bis" variant="outlined" density="compact" @update:model-value="loadEur" /></v-col>
        </v-row>
        <v-table density="compact" v-if="eurData">
          <tbody>
            <tr><td class="text-medium-emphasis">Einnahmen (Zahlungseingänge brutto)</td><td class="text-right text-success"><strong>+ {{ fmtEur(eurData.einnahmen_brutto) }}</strong></td></tr>
            <tr><td class="text-medium-emphasis pl-4">davon Soll-USt</td><td class="text-right">{{ fmtEur(eurData.soll_ust) }}</td></tr>
            <tr><td class="text-medium-emphasis">Betriebsausgaben (Eingangsrechnungen netto)</td><td class="text-right text-error"><strong>− {{ fmtEur(eurData.ausgaben_netto) }}</strong></td></tr>
            <tr><td class="text-medium-emphasis pl-4">davon Vorsteuer</td><td class="text-right">{{ fmtEur(eurData.ausgaben_ust) }}</td></tr>
            <tr style="border-top:2px solid #ccc">
              <td><strong>Gewinn / Verlust (Netto)</strong></td>
              <td class="text-right"><strong :class="eurData.gewinn_verlust >= 0 ? 'text-success' : 'text-error'">{{ fmtEur(eurData.gewinn_verlust) }}</strong></td>
            </tr>
          </tbody>
        </v-table>
        <div v-if="eurData" class="text-caption text-medium-emphasis mt-2">
          Basis: {{ eurData.payments_count }} Zahlungseingänge + {{ eurData.supplier_invoices_count }} bezahlte Eingangsrechnungen
        </div>
        <v-alert type="info" variant="tonal" density="compact" class="mt-2" icon="mdi-information-outline">
          Vereinfachte Vorschau — keine Steuerberatung. Maßgeblich ist die Auswertung Ihres Steuerberaters.
        </v-alert>
      </v-card-text>
    </v-card>

    <!-- Marge pro Auftrag -->
    <v-card class="mb-4">
      <v-card-title class="d-flex align-center">
        Marge pro Auftrag
        <v-spacer />
        <v-btn size="small" icon variant="text" :loading="marginLoading" @click="loadMargin"><v-icon>mdi-refresh</v-icon></v-btn>
      </v-card-title>
      <v-table density="compact">
        <thead>
          <tr>
            <th>Auftragsnr.</th>
            <th>Titel</th>
            <th>Kunde</th>
            <th>Status</th>
            <th class="text-right">Std. Ist</th>
            <th class="text-right">Std. Verr.</th>
            <th class="text-right">Zeitkosten €</th>
            <th class="text-right">Fakturiert €</th>
            <th class="text-right">Marge €</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="marginLoading">
            <td colspan="9" class="text-center pa-4"><v-progress-circular indeterminate size="24" /></td>
          </tr>
          <tr v-else-if="!marginRows.length">
            <td colspan="9" class="text-center pa-4 text-medium-emphasis">Keine Aufträge</td>
          </tr>
          <tr v-for="r in marginRows" :key="r.order_id">
            <td><strong>{{ r.order_no }}</strong></td>
            <td>{{ r.title }}</td>
            <td>{{ r.customer }}</td>
            <td><v-chip size="x-small" :color="orderStatusColor(r.status)" label>{{ orderStatusLabel(r.status) }}</v-chip></td>
            <td class="text-right">{{ r.hours_total.toFixed(1) }}</td>
            <td class="text-right">{{ r.hours_billable.toFixed(1) }}</td>
            <td class="text-right">{{ fmtEur(r.time_cost) }}</td>
            <td class="text-right">{{ fmtEur(r.invoiced_total) }}</td>
            <td class="text-right" :class="r.marge >= 0 ? 'text-success' : 'text-error'">
              <strong>{{ fmtEur(r.marge) }}</strong>
            </td>
          </tr>
          <tr v-if="marginRows.length" style="background:#f5f5f5">
            <td colspan="6"><strong>Gesamt</strong></td>
            <td class="text-right"><strong>{{ fmtEur(marginTotal.cost) }}</strong></td>
            <td class="text-right"><strong>{{ fmtEur(marginTotal.invoiced) }}</strong></td>
            <td class="text-right" :class="marginTotal.marge >= 0 ? 'text-success' : 'text-error'">
              <strong>{{ fmtEur(marginTotal.marge) }}</strong>
            </td>
          </tr>
        </tbody>
      </v-table>
      <v-card-text v-if="marginRows.some(r => r.time_cost === 0 && r.hours_billable > 0)">
        <v-alert type="info" variant="tonal" density="compact" icon="mdi-information-outline">
          Zeiteinträge ohne Stundensatz werden mit 0 € bewertet. Stundensatz bei Zeitbuchungen eintragen für genaue Margenkalkulation.
        </v-alert>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/api/client'

const auth = useAuthStore()

const today = new Date().toISOString().slice(0, 10)
const firstOfMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10)
const fmtEur = (v: number) => `${v.toFixed(2)} €`

// ── Steuerberater-Export ────────────────────────────────────────────────────
const exportFrom = ref(firstOfMonth)
const exportTo = ref(today)
const exporting = ref(false)
const exportError = ref('')

async function doExport() {
  exporting.value = true; exportError.value = ''
  try {
    const token = auth.accessToken
    const tenantId = auth.currentTenant?.id
    const url = `/api/v1/reports/export/tax?period_from=${exportFrom.value}&period_to=${exportTo.value}`
    const res = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
        ...(tenantId ? { 'X-Tenant-ID': String(tenantId) } : {}),
      },
    })
    if (!res.ok) { exportError.value = `Fehler: ${res.statusText}`; return }
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `steuerberater_${exportFrom.value}_${exportTo.value}.zip`
    a.click(); URL.revokeObjectURL(a.href)
  } catch (e) { exportError.value = e instanceof Error ? e.message : 'Export fehlgeschlagen' }
  finally { exporting.value = false }
}

// ── DATEV-Export ────────────────────────────────────────────────────────────
const datevFrom = ref(firstOfMonth)
const datevTo = ref(today)
const datevExporting = ref(false)

async function doDatevExport() {
  datevExporting.value = true
  try {
    const token = auth.accessToken
    const tenantId = auth.currentTenant?.id
    const url = `/api/v1/reports/export/datev?period_from=${datevFrom.value}&period_to=${datevTo.value}`
    const res = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`,
        ...(tenantId ? { 'X-Tenant-ID': String(tenantId) } : {}),
      },
    })
    if (!res.ok) return
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `datev_${datevFrom.value}_${datevTo.value}.csv`
    a.click(); URL.revokeObjectURL(a.href)
  } finally { datevExporting.value = false }
}

// ── USt-Vorschau ────────────────────────────────────────────────────────────
const vatFrom = ref(firstOfMonth)
const vatTo = ref(today)
const vatLoading = ref(false)
const vatData = ref<{ soll_ust: number; vorsteuer: number; zahllast: number; invoices_count: number; supplier_invoices_count: number } | null>(null)

async function loadVat() {
  vatLoading.value = true
  try { vatData.value = await api.get(`/reports/vat-preview?period_from=${vatFrom.value}&period_to=${vatTo.value}`) }
  catch { vatData.value = null }
  finally { vatLoading.value = false }
}

// ── EÜR-Vorschau ────────────────────────────────────────────────────────────
const eurFrom = ref(new Date(new Date().getFullYear(), 0, 1).toISOString().slice(0, 10))
const eurTo = ref(today)
const eurLoading = ref(false)
const eurData = ref<{
  einnahmen_brutto: number; einnahmen_netto: number; soll_ust: number
  ausgaben_netto: number; ausgaben_ust: number; gewinn_verlust: number
  payments_count: number; supplier_invoices_count: number
} | null>(null)

async function loadEur() {
  eurLoading.value = true
  try { eurData.value = await api.get(`/reports/eur?period_from=${eurFrom.value}&period_to=${eurTo.value}`) }
  catch { eurData.value = null }
  finally { eurLoading.value = false }
}

// ── Marge pro Auftrag ───────────────────────────────────────────────────────
interface MarginRow {
  order_id: number; order_no: string; title: string; customer: string; status: string
  hours_total: number; hours_billable: number; time_cost: number; invoiced_total: number; marge: number
}

const marginLoading = ref(false)
const marginRows = ref<MarginRow[]>([])
const marginTotal = computed(() => ({
  cost: marginRows.value.reduce((s, r) => s + r.time_cost, 0),
  invoiced: marginRows.value.reduce((s, r) => s + r.invoiced_total, 0),
  marge: marginRows.value.reduce((s, r) => s + r.marge, 0),
}))

const ORDER_STATUS_LABELS: Record<string, string> = { open: 'Offen', in_progress: 'In Arbeit', done: 'Abgeschlossen', cancelled: 'Storniert' }
const ORDER_STATUS_COLORS: Record<string, string> = { open: 'info', in_progress: 'warning', done: 'success', cancelled: 'default' }
const orderStatusLabel = (s: string) => ORDER_STATUS_LABELS[s] ?? s
const orderStatusColor = (s: string) => ORDER_STATUS_COLORS[s] ?? 'default'

async function loadMargin() {
  marginLoading.value = true
  try { marginRows.value = await api.get('/reports/margin') }
  catch { marginRows.value = [] }
  finally { marginLoading.value = false }
}

onMounted(() => { loadVat(); loadMargin(); loadEur() })
</script>
