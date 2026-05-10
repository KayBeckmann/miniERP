<template>
  <v-app>
    <AppNavDrawer v-model:open="drawerOpen" />

    <v-app-bar color="primary" elevation="2">
      <v-app-bar-nav-icon @click="drawerOpen = !drawerOpen" />
      <v-app-bar-title>miniERP</v-app-bar-title>

      <v-spacer />

      <!-- Mandantenwahl -->
      <TenantSwitcher />

      <!-- Profil-Menü -->
      <v-menu location="bottom end">
        <template #activator="{ props }">
          <v-btn icon v-bind="props">
            <v-icon>mdi-account-circle</v-icon>
            <v-tooltip activator="parent">Profil</v-tooltip>
          </v-btn>
        </template>
        <v-list density="compact" min-width="200">
          <v-list-item :subtitle="auth.user?.email ?? ''" prepend-icon="mdi-account">
            <template #title><strong>Profil</strong></template>
          </v-list-item>
          <v-divider />
          <v-list-item prepend-icon="mdi-lock-reset" title="Passwort ändern" @click="pwDialog = true" />
          <v-divider />
          <v-list-item prepend-icon="mdi-logout" title="Abmelden" base-color="error"
            @click="auth.logout(); router.push('/login')" />
        </v-list>
      </v-menu>
    </v-app-bar>

    <v-main>
      <v-container fluid class="pa-4">
        <router-view />
      </v-container>
    </v-main>

    <!-- Passwort ändern Dialog -->
    <v-dialog v-model="pwDialog" max-width="420" persistent>
      <v-card>
        <v-card-title>Passwort ändern</v-card-title>
        <v-card-text>
          <v-text-field v-model="pwForm.current" label="Aktuelles Passwort" type="password"
            variant="outlined" density="compact" class="mb-2" :error-messages="pwError ? [pwError] : []" />
          <v-text-field v-model="pwForm.next" label="Neues Passwort" type="password"
            variant="outlined" density="compact" class="mb-2"
            hint="Mindestens 8 Zeichen" persistent-hint />
          <v-text-field v-model="pwForm.confirm" label="Neues Passwort wiederholen" type="password"
            variant="outlined" density="compact"
            :error-messages="pwForm.confirm && pwForm.next !== pwForm.confirm ? ['Passwörter stimmen nicht überein'] : []" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="closePwDialog">Abbrechen</v-btn>
          <v-btn color="primary" variant="flat" :loading="pwSaving"
            :disabled="!pwForm.current || !pwForm.next || pwForm.next !== pwForm.confirm"
            @click="changePassword">
            Speichern
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

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
import { api } from '@/api/client'
import AppNavDrawer from '@/components/layout/AppNavDrawer.vue'
import TenantSwitcher from '@/components/layout/TenantSwitcher.vue'

const drawerOpen = ref(true)
const auth = useAuthStore()
const snackbar = useSnackbarStore()
const router = useRouter()

// ── Passwort ändern ──────────────────────────────────────────────────────────
const pwDialog = ref(false)
const pwSaving = ref(false)
const pwError = ref('')
const pwForm = ref({ current: '', next: '', confirm: '' })

function closePwDialog() {
  pwDialog.value = false
  pwForm.value = { current: '', next: '', confirm: '' }
  pwError.value = ''
}

async function changePassword() {
  pwSaving.value = true
  pwError.value = ''
  try {
    await api.post('/auth/change-password', {
      current_password: pwForm.value.current,
      new_password: pwForm.value.next,
    })
    closePwDialog()
    snackbar.notify('Passwort erfolgreich geändert')
  } catch (e) {
    pwError.value = e instanceof Error ? e.message : 'Fehler beim Ändern'
  } finally {
    pwSaving.value = false
  }
}
</script>
