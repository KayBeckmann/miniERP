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
        v-for="item in navItems"
        :key="item.route"
        :prepend-icon="item.icon"
        :title="item.title"
        :to="item.route"
        :active="route.name === item.name"
        color="primary"
      />
    </v-list>
  </v-navigation-drawer>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

defineProps<{ open: boolean }>()
defineEmits<{ 'update:open': [value: boolean] }>()

const route = useRoute()

const navItems = [
  { name: 'dashboard', route: '/dashboard', icon: 'mdi-view-dashboard', title: 'Dashboard' },
  { name: 'customers', route: '/customers', icon: 'mdi-account-group', title: 'Kunden' },
  { name: 'quotes', route: '/quotes', icon: 'mdi-file-document', title: 'Angebote' },
  { name: 'orders', route: '/orders', icon: 'mdi-clipboard-list', title: 'Aufträge' },
  { name: 'invoices', route: '/invoices', icon: 'mdi-receipt', title: 'Rechnungen' },
  { name: 'time', route: '/time', icon: 'mdi-clock-outline', title: 'Stundenerfassung' },
  {
    name: 'supplier-invoices',
    route: '/supplier-invoices',
    icon: 'mdi-truck-delivery',
    title: 'Eingangsrechnungen',
  },
  { name: 'reports', route: '/reports', icon: 'mdi-chart-bar', title: 'Auswertungen' },
]
</script>
