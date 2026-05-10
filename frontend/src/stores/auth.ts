import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Tenant } from '@/api/types'

interface User { id: number; email: string; role: string }

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const currentTenant = ref<Tenant | null>(
    JSON.parse(localStorage.getItem('current_tenant') ?? 'null'),
  )
  const user = ref<User | null>(
    JSON.parse(localStorage.getItem('auth_user') ?? 'null'),
  )

  const isAuthenticated = computed(() => !!accessToken.value)

  function setToken(token: string) {
    accessToken.value = token
    localStorage.setItem('access_token', token)
  }

  function setUser(u: User) {
    user.value = u
    localStorage.setItem('auth_user', JSON.stringify(u))
  }

  function setTenant(tenant: Tenant) {
    currentTenant.value = tenant
    localStorage.setItem('current_tenant', JSON.stringify(tenant))
  }

  function logout() {
    accessToken.value = null
    currentTenant.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('current_tenant')
    localStorage.removeItem('auth_user')
  }

  return { accessToken, currentTenant, user, isAuthenticated, setToken, setUser, setTenant, logout }
})
