<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card elevation="4" rounded="lg">
          <v-card-title class="pt-6 pb-2 text-center">
            <v-icon size="48" color="primary" class="d-block mx-auto mb-2">mdi-home-city</v-icon>
            <span class="text-h5">miniERP</span>
          </v-card-title>

          <v-card-subtitle class="text-center pb-4">
            Bau &amp; Hufbearbeitung
          </v-card-subtitle>

          <v-card-text>
            <v-form ref="formRef" @submit.prevent="login">
              <v-text-field
                v-model="email"
                label="E-Mail"
                type="email"
                prepend-inner-icon="mdi-email"
                :rules="[required]"
                autocomplete="username"
                variant="outlined"
                density="comfortable"
                class="mb-2"
              />
              <v-text-field
                v-model="password"
                label="Passwort"
                :type="showPassword ? 'text' : 'password'"
                prepend-inner-icon="mdi-lock"
                :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                :rules="[required]"
                autocomplete="current-password"
                variant="outlined"
                density="comfortable"
                @click:append-inner="showPassword = !showPassword"
              />

              <v-alert
                v-if="error"
                type="error"
                variant="tonal"
                density="compact"
                class="mt-2 mb-0"
              >
                {{ error }}
              </v-alert>
            </v-form>
          </v-card-text>

          <v-card-actions class="px-4 pb-6">
            <v-btn
              block
              color="primary"
              size="large"
              :loading="loading"
              type="submit"
              @click="login"
            >
              Anmelden
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { TokenResponse } from '@/api/types'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')
const formRef = ref()

const required = (v: string) => !!v || 'Pflichtfeld'

async function login() {
  error.value = ''
  const { valid } = await formRef.value.validate()
  if (!valid) return

  loading.value = true
  try {
    const body = new URLSearchParams({ username: email.value, password: password.value })
    const res = await fetch('/api/v1/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.detail ?? 'Ungültige Zugangsdaten')
    }
    const data: TokenResponse = await res.json()
    auth.setToken(data.access_token)
    router.push('/dashboard')
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Anmeldung fehlgeschlagen'
  } finally {
    loading.value = false
  }
}
</script>
