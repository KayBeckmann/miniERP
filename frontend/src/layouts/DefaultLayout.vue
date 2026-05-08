<template>
  <v-app>
    <AppNavDrawer v-model:open="drawerOpen" />

    <v-app-bar color="primary" elevation="2">
      <v-app-bar-nav-icon @click="drawerOpen = !drawerOpen" />
      <v-app-bar-title>miniERP</v-app-bar-title>

      <v-spacer />

      <!-- Mandantenwahl -->
      <TenantSwitcher />

      <v-btn icon @click="auth.logout(); router.push('/login')">
        <v-icon>mdi-logout</v-icon>
        <v-tooltip activator="parent">Abmelden</v-tooltip>
      </v-btn>
    </v-app-bar>

    <v-main>
      <v-container fluid class="pa-4">
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppNavDrawer from '@/components/layout/AppNavDrawer.vue'
import TenantSwitcher from '@/components/layout/TenantSwitcher.vue'

const drawerOpen = ref(true)
const auth = useAuthStore()
const router = useRouter()
</script>
