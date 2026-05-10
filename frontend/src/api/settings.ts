import { api } from '@/api/client'

export interface TenantSettings {
  id: number
  code: string
  name: string
  address: string | null
  iban: string | null
  pdf_color: string
  pdf_footer_text: string | null
  pdf_show_bank_details: boolean
  pdf_accent_secondary: string
}

export interface TenantSettingsUpdate {
  name?: string
  address?: string | null
  iban?: string | null
  pdf_color?: string
  pdf_footer_text?: string | null
  pdf_show_bank_details?: boolean
  pdf_accent_secondary?: string
}

export const settingsApi = {
  getTenant: () => api.get<TenantSettings>('/settings/tenant'),
  updateTenant: (body: TenantSettingsUpdate) => api.patch<TenantSettings>('/settings/tenant', body),
}
