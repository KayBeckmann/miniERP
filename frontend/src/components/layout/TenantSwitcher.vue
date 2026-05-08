<template>
  <v-btn-toggle
    v-model="selectedCode"
    mandatory
    color="white"
    variant="outlined"
    class="mr-2"
    @update:model-value="onSwitch"
  >
    <v-btn
      v-for="t in tenants"
      :key="t.code"
      :value="t.code"
      size="small"
    >
      <v-icon start>{{ t.icon }}</v-icon>
      {{ t.name }}
    </v-btn>
  </v-btn-toggle>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import type { Tenant, TenantCode } from '@/api/types'

const auth = useAuthStore()

const tenants: (Tenant & { icon: string })[] = [
  { id: 1, code: 'bau', name: 'Bau', icon: 'mdi-home-city-outline' },
  { id: 2, code: 'huf', name: 'Hufbearbeitung', icon: 'mdi-horse' },
]

const selectedCode = ref<TenantCode>(auth.currentTenant?.code ?? 'bau')

function onSwitch(code: TenantCode) {
  const t = tenants.find((x) => x.code === code)
  if (t) auth.setTenant(t)
}

// Set default tenant on mount if none is set
if (!auth.currentTenant) {
  auth.setTenant(tenants[0])
}
</script>
