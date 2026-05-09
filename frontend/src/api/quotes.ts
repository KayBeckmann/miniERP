import { api } from './client'

export type QuoteStatus = 'draft' | 'sent' | 'accepted' | 'declined' | 'expired'

export interface QuoteItem {
  id: number
  quote_id: number
  position: number
  description: string
  qty: string
  unit: string
  unit_price: string
  discount_pct: string
  vat_rate: string
  line_total: string
  material_id: number | null
}

export interface Quote {
  id: number
  tenant_id: number
  customer_id: number
  quote_no: string
  quote_date: string
  valid_until: string | null
  status: QuoteStatus
  subtotal: string
  vat_total: string
  total: string
  notes: string | null
  internal_notes: string | null
  pdf_path: string | null
  version: number
  created_at: string
  updated_at: string
  items: QuoteItem[]
}

export interface QuoteItemIn {
  description: string
  qty: string
  unit: string
  unit_price: string
  discount_pct?: string
  vat_rate: string
  material_id?: number | null
  position?: number | null
}

export interface QuoteCreate {
  customer_id: number
  quote_date: string
  valid_until?: string | null
  notes?: string | null
  internal_notes?: string | null
  items: QuoteItemIn[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
}

export interface PositionHistory {
  id: number
  description: string
  unit: string
  unit_price: string
  vat_rate: string
  usage_count: number
}

export const STATUS_LABELS: Record<QuoteStatus, string> = {
  draft: 'Entwurf',
  sent: 'Gesendet',
  accepted: 'Angenommen',
  declined: 'Abgelehnt',
  expired: 'Abgelaufen',
}

export const STATUS_COLORS: Record<QuoteStatus, string> = {
  draft: 'default',
  sent: 'info',
  accepted: 'success',
  declined: 'error',
  expired: 'warning',
}

export const TRANSITIONS: Record<QuoteStatus, QuoteStatus[]> = {
  draft: ['sent', 'expired'],
  sent: ['accepted', 'declined', 'expired'],
  accepted: ['draft'],
  declined: [],
  expired: [],
}

function qp(p: Record<string, string | number | boolean | undefined>): string {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(p)) {
    if (v !== undefined && v !== '') q.set(k, String(v))
  }
  return q.toString() ? `?${q}` : ''
}

export const quotesApi = {
  list: (p: { skip?: number; limit?: number; search?: string; status?: string } = {}) =>
    api.get<PaginatedResponse<Quote>>(`/quotes${qp(p)}`),
  get: (id: number) => api.get<Quote>(`/quotes/${id}`),
  create: (data: QuoteCreate) => api.post<Quote>('/quotes', data),
  update: (id: number, data: Partial<QuoteCreate> & { items?: QuoteItemIn[] }) =>
    api.patch<Quote>(`/quotes/${id}`, data),
  delete: (id: number) => api.delete<void>(`/quotes/${id}`),
  setStatus: (id: number, status: QuoteStatus) =>
    api.patch<Quote>(`/quotes/${id}/status`, { status }),
  duplicate: (id: number) => api.post<Quote>(`/quotes/${id}/duplicate`, {}),
  pdfUrl: (id: number) => `/api/v1/quotes/${id}/pdf`,
  positionHistory: (search?: string) =>
    api.get<PositionHistory[]>(`/quotes/position-history${search ? `?search=${encodeURIComponent(search)}` : ''}`),
}
