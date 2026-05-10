<template>
  <v-navigation-drawer :model-value="open" @update:model-value="$emit('update:open', $event)">
    <v-list-item
      prepend-icon="mdi-home-city"
      title="miniERP"
      subtitle="Bau & Hufbearbeitung"
      nav
    />

    <v-divider />

    <v-list density="compact" nav>
      <v-list-item
        prepend-icon="mdi-view-dashboard"
        title="Dashboard"
        to="/dashboard"
        color="primary"
      />

      <v-list-subheader>Stammdaten</v-list-subheader>
      <v-list-item prepend-icon="mdi-account-group" title="Kunden" to="/customers" color="primary" />
      <v-list-item prepend-icon="mdi-truck-delivery-outline" title="Lieferanten" to="/suppliers" color="primary" />
      <v-list-item prepend-icon="mdi-package-variant" title="Materialstamm" to="/materials" color="primary" />

      <v-list-subheader>Belege</v-list-subheader>
      <v-list-item prepend-icon="mdi-file-document-outline" title="Angebote" to="/quotes" color="primary" />
      <v-list-item prepend-icon="mdi-clipboard-list-outline" title="Aufträge" to="/orders" color="primary" />
      <v-list-item prepend-icon="mdi-receipt-text-outline" title="Rechnungen" to="/invoices" color="primary" />

      <v-list-subheader>Erfassung</v-list-subheader>
      <v-list-item prepend-icon="mdi-clock-outline" title="Stundenerfassung" to="/time" color="primary" />
      <v-list-item prepend-icon="mdi-file-import-outline" title="Eingangsrechnungen" to="/supplier-invoices" color="primary" />

      <v-list-subheader>Auswertung</v-list-subheader>
      <v-list-item prepend-icon="mdi-chart-bar" title="Auswertungen" to="/reports" color="primary" />

      <v-list-subheader>Einstellungen</v-list-subheader>
      <v-list-item prepend-icon="mdi-file-pdf-box" title="PDF-Vorlagen" to="/pdf-settings" color="primary" />
    </v-list>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
defineProps<{ open: boolean }>()
defineEmits<{ 'update:open': [value: boolean] }>()
</script>
