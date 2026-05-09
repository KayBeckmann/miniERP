<template>
  <div>
    <h1 class="text-h5 mb-1">Dashboard</h1>
    <p class="text-caption text-medium-emphasis mb-4">Mandant: {{ auth.currentTenant?.name ?? '—' }}</p>

    <v-row class="mb-2">
      <v-col v-for="card in summaryCards" :key="card.title" cols="12" sm="6" md="4" lg="2">
        <v-card :color="card.color" variant="tonal" rounded="lg" :to="card.to" style="cursor:pointer">
          <v-card-text>
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="text-caption text-medium-emphasis">{{ card.title }}</div>
                <div class="text-h6 font-weight-bold mt-1">
                  <template v-if="loading">—</template>
                  <template v-else>{{ card.value }}</template>
                </div>
                <div v-if="card.sub" class="text-caption">{{ card.sub }}</div>
              </div>
              <v-icon size="32" :color="card.color">{{ card.icon }}</v-icon>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-alert v-if="loadError" type="warning" variant="tonal" density="compact" class="mb-4">
      Dashboard-Daten konnten nicht geladen werden — Backend prüfen.
    </v-alert>

    <v-row>
      <!-- Letzte Angebote -->
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="d-flex align-center py-3 px-4">
            Letzte Angebote
            <v-spacer />
            <v-btn size="small" variant="text" :to="{ name: 'quotes' }">Alle</v-btn>
          </v-card-title>
          <v-table density="compact">
            <tbody>
              <tr v-if="loading"><td class="text-center pa-3"><v-progress-circular indeterminate size="20" /></td></tr>
              <tr v-else-if="!data?.recent_quotes?.length"><td class="text-center pa-3 text-medium-emphasis text-caption">Keine Angebote</td></tr>
              <tr v-for="q in data?.recent_quotes" :key="q.id" style="cursor:pointer"
                @click="$router.push({ name: 'quote-edit', params: { id: q.id } })">
                <td><strong>{{ q.quote_no }}</strong></td>
                <td><v-chip :color="STATUS_COLORS_Q[q.status]" size="x-small" label>{{ STATUS_LABELS_Q[q.status] }}</v-chip></td>
                <td class="text-right">{{ fmtEur(q.total) }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </v-col>

      <!-- Letzte Rechnungen -->
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title class="d-flex align-center py-3 px-4">
            Letzte Rechnungen
            <v-spacer />
            <v-btn size="small" variant="text" :to="{ name: 'invoices' }">Alle</v-btn>
          </v-card-title>
          <v-table density="compact">
            <tbody>
              <tr v-if="loading"><td class="text-center pa-3"><v-progress-circular indeterminate size="20" /></td></tr>
              <tr v-else-if="!data?.recent_invoices?.length"><td class="text-center pa-3 text-medium-emphasis text-caption">Keine Rechnungen</td></tr>
              <tr v-for="inv in data?.recent_invoices" :key="inv.id">
                <td><strong>{{ inv.invoice_no }}</strong></td>
                <td class="text-truncate" style="max-width:120px">{{ inv.customer }}</td>
                <td><v-chip :color="STATUS_COLORS_I[inv.status]" size="x-small" label>{{ STATUS_LABELS_I[inv.status] }}</v-chip></td>
                <td class="text-right">{{ fmtEur(inv.total) }}</td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/api/client'

const auth = useAuthStore()
const loading = ref(true)
const loadError = ref(false)

interface DashboardData {
  quotes_open: number; orders_open: number
  invoices_open: number; invoices_open_total: string; invoices_overdue: number
  hours_this_month: number; hours_this_week: number
  recent_quotes: { id: number; quote_no: string; status: string; total: string }[]
  recent_invoices: { id: number; invoice_no: string; status: string; total: string; customer: string }[]
}

const data = ref<DashboardData | null>(null)
const fmtEur = (v: string | number) => `${Number(v).toFixed(2)} €`

const STATUS_COLORS_Q: Record<string, string> = { draft: 'default', sent: 'info', accepted: 'success', declined: 'error', expired: 'warning' }
const STATUS_LABELS_Q: Record<string, string> = { draft: 'Entwurf', sent: 'Gesendet', accepted: 'Angenommen', declined: 'Abgelehnt', expired: 'Abgelaufen' }
const STATUS_COLORS_I: Record<string, string> = { draft: 'default', sent: 'info', paid: 'success', overdue: 'error', cancelled: 'default' }
const STATUS_LABELS_I: Record<string, string> = { draft: 'Entwurf', sent: 'Offen', paid: 'Bezahlt', overdue: 'Überfällig', cancelled: 'Storniert' }

const summaryCards = computed(() => [
  { title: 'Offene Angebote', value: data.value?.quotes_open ?? '—', icon: 'mdi-file-document-outline', color: 'info', to: '/quotes' },
  { title: 'Offene Aufträge', value: data.value?.orders_open ?? '—', icon: 'mdi-clipboard-list-outline', color: 'primary', to: '/orders' },
  {
    title: 'Offene Rechnungen', value: data.value?.invoices_open ?? '—',
    sub: data.value?.invoices_open_total ? fmtEur(data.value.invoices_open_total) : undefined,
    icon: 'mdi-receipt-text-outline', color: 'warning', to: '/invoices',
  },
  { title: 'Überfällig', value: data.value?.invoices_overdue ?? '—', icon: 'mdi-alert-circle-outline', color: 'error', to: '/invoices' },
  {
    title: 'Std. diese Woche',
    value: data.value?.hours_this_week !== undefined ? `${data.value.hours_this_week} h` : '—',
    icon: 'mdi-clock-outline', color: 'success', to: '/time',
  },
  {
    title: 'Std. diesen Monat',
    value: data.value?.hours_this_month !== undefined ? `${data.value.hours_this_month} h` : '—',
    icon: 'mdi-calendar-month-outline', color: 'teal', to: '/time',
  },
])

onMounted(async () => {
  loading.value = true
  try { data.value = await api.get<DashboardData>('/reports/dashboard') }
  catch { loadError.value = true }
  finally { loading.value = false }
})
</script>
