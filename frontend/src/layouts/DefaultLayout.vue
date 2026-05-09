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

    <!-- Global Snackbar -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.type" :timeout="snackbar.timeout"
      location="bottom right" rounded="lg">
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false"><v-icon>mdi-close</v-icon></v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSnackbarStore } from '@/stores/snackbar'
import AppNavDrawer from '@/components/layout/AppNavDrawer.vue'
import TenantSwitcher from '@/components/layout/TenantSwitcher.vue'

const drawerOpen = ref(true)
const auth = useAuthStore()
const snackbar = useSnackbarStore()
const router = useRouter()
</script>
