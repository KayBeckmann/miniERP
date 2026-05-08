<template>
  <div>
    <h1 class="text-h5 mb-4">Dashboard — {{ auth.currentTenant?.name ?? 'miniERP' }}</h1>

    <v-row>
      <v-col
        v-for="card in summaryCards"
        :key="card.title"
        cols="12"
        sm="6"
        md="4"
        lg="3"
      >
        <v-card :color="card.color" variant="tonal" rounded="lg">
          <v-card-text>
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="text-caption text-medium-emphasis">{{ card.title }}</div>
                <div class="text-h6 font-weight-bold mt-1">{{ card.value }}</div>
              </div>
              <v-icon size="36" :color="card.color">{{ card.icon }}</v-icon>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-alert type="info" variant="tonal" class="mt-6" density="compact">
      Phase 0 — Backend noch nicht verbunden. Daten werden angezeigt sobald das Backend läuft.
    </v-alert>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const summaryCards = [
  { title: 'Offene Angebote', value: '—', icon: 'mdi-file-document', color: 'info' },
  { title: 'Offene Aufträge', value: '—', icon: 'mdi-clipboard-list', color: 'primary' },
  { title: 'Offene Rechnungen', value: '—', icon: 'mdi-receipt', color: 'warning' },
  { title: 'Überfällige Rechnungen', value: '—', icon: 'mdi-alert-circle', color: 'error' },
  { title: 'Fällige Eingangsrechnungen', value: '—', icon: 'mdi-truck-delivery', color: 'secondary' },
  { title: 'Stunden diesen Monat', value: '—', icon: 'mdi-clock-outline', color: 'success' },
]
</script>
