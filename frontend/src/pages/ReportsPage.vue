<template>
  <div>
    <h1 class="text-h5 mb-4">Auswertungen</h1>

    <v-card class="mb-4">
      <v-card-title>Steuerberater-Export</v-card-title>
      <v-card-text>
        <p class="text-body-2 text-medium-emphasis mb-4">
          Zip-Bundle mit Ausgangsrechnungen CSV + Zahlungen CSV + manifest.json für den gewählten Zeitraum.
        </p>
        <v-row dense>
          <v-col cols="12" sm="4">
            <v-text-field v-model="exportFrom" type="date" label="Von" variant="outlined" density="compact" />
          </v-col>
          <v-col cols="12" sm="4">
            <v-text-field v-model="exportTo" type="date" label="Bis" variant="outlined" density="compact" />
          </v-col>
          <v-col cols="12" sm="4" class="d-flex align-center">
            <v-btn color="primary" :loading="exporting" prepend-icon="mdi-download" @click="doExport">
              Export herunterladen
            </v-btn>
          </v-col>
        </v-row>
        <v-alert v-if="exportError" type="error" variant="tonal" density="compact" class="mt-2">{{ exportError }}</v-alert>
      </v-card-text>
    </v-card>

    <v-alert type="info" variant="tonal" density="compact">
      Weitere Auswertungen (Marge pro Auftrag, USt-Vorschau, OP-Liste) folgen in Phase 6.
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const today = new Date().toISOString().slice(0, 10)
const firstOfMonth = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10)
const exportFrom = ref(firstOfMonth)
const exportTo = ref(today)
const exporting = ref(false)
const exportError = ref('')

async function doExport() {
  exporting.value = true
  exportError.value = ''
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
    a.click()
    URL.revokeObjectURL(a.href)
  } catch (e) {
    exportError.value = e instanceof Error ? e.message : 'Export fehlgeschlagen'
  } finally {
    exporting.value = false
  }
}
</script>
