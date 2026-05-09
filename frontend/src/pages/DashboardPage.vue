<template>
  <div>
    <h1 class="text-h5 mb-1">Dashboard</h1>
    <p class="text-caption text-medium-emphasis mb-4">Mandant: {{ auth.currentTenant?.name ?? '—' }}</p>

    <v-row>
      <v-col v-for="card in summaryCards" :key="card.title" cols="12" sm="6" md="4" lg="3">
        <v-card :color="card.color" variant="tonal" rounded="lg" :to="card.to">
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
              <v-icon size="36" :color="card.color">{{ card.icon }}</v-icon>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-alert v-if="loadError" type="warning" variant="tonal" density="compact" class="mt-4">
      Dashboard-Daten konnten nicht geladen werden — Backend prüfen.
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/api/client'

const auth = useAuthStore()
const loading = ref(true)
const loadError = ref(false)
const data = ref<Record<string, string | number> | null>(null)

const fmtEur = (v: string | number | undefined) =>
  v !== undefined ? `${Number(v).toFixed(2)} €` : '—'

const summaryCards = computed(() => [
  { title: 'Offene Angebote', value: data.value?.quotes_open ?? '—', icon: 'mdi-file-document-outline', color: 'info', to: '/quotes' },
  { title: 'Offene Aufträge', value: data.value?.orders_open ?? '—', icon: 'mdi-clipboard-list-outline', color: 'primary', to: '/orders' },
  {
    title: 'Offene Rechnungen', value: data.value?.invoices_open ?? '—',
    sub: data.value?.invoices_open_total ? fmtEur(data.value.invoices_open_total) : undefined,
    icon: 'mdi-receipt-text-outline', color: 'warning', to: '/invoices',
  },
  { title: 'Überfällige Rechnungen', value: data.value?.invoices_overdue ?? '—', icon: 'mdi-alert-circle-outline', color: 'error', to: '/invoices' },
  { title: 'Stunden diesen Monat', value: data.value?.hours_this_month !== undefined ? `${data.value.hours_this_month} h` : '—', icon: 'mdi-clock-outline', color: 'success', to: '/orders' },
])

onMounted(async () => {
  loading.value = true
  try {
    data.value = await api.get<Record<string, string | number>>('/reports/dashboard')
  } catch {
    loadError.value = true
  } finally {
    loading.value = false
  }
})
</script>
