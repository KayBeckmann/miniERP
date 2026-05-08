export type TenantCode = 'bau' | 'huf'

export interface Tenant {
  id: number
  code: TenantCode
  name: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface ApiError {
  detail: string
}
