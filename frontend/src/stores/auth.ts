import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Tenant } from '@/api/types'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const currentTenant = ref<Tenant | null>(
    JSON.parse(localStorage.getItem('current_tenant') ?? 'null'),
  )

  const isAuthenticated = computed(() => !!accessToken.value)

  function setToken(token: string) {
    accessToken.value = token
    localStorage.setItem('access_token', token)
  }

  function setTenant(tenant: Tenant) {
    currentTenant.value = tenant
    localStorage.setItem('current_tenant', JSON.stringify(tenant))
  }

  function logout() {
    accessToken.value = null
    currentTenant.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('current_tenant')
  }

  return { accessToken, currentTenant, isAuthenticated, setToken, setTenant, logout }
})
