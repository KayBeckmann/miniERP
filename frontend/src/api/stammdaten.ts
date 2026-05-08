import { api } from './client'

export interface PaginatedResponse<T> {
  items: T[]
  total: number
}

// ── Customers ──────────────────────────────────────────────────────────────

export interface Customer {
  id: number
  tenant_id: number
  customer_no: string
  kind: 'privat' | 'geschaeft'
  name: string
  contact: string | null
  address: string | null
  email: string | null
  phone: string | null
  tax_id: string | null
  notes: string | null
  is_business: boolean
  e_invoice_format: 'none' | 'xrechnung' | 'zugferd'
  leitweg_id: string | null
  active: boolean
  created_at: string
}

export type CustomerCreate = Omit<Customer, 'id' | 'tenant_id' | 'customer_no' | 'created_at'>
export type CustomerUpdate = Partial<CustomerCreate>

function listParams(p: { skip?: number; limit?: number; search?: string }): string {
  const q = new URLSearchParams()
  if (p.skip) q.set('skip', String(p.skip))
  if (p.limit) q.set('limit', String(p.limit))
  if (p.search) q.set('search', p.search)
  return q.toString() ? `?${q}` : ''
}

export const customersApi = {
  list: (p: { skip?: number; limit?: number; search?: string } = {}) =>
    api.get<PaginatedResponse<Customer>>(`/customers${listParams(p)}`),
  get: (id: number) => api.get<Customer>(`/customers/${id}`),
  create: (data: CustomerCreate) => api.post<Customer>('/customers', data),
  update: (id: number, data: CustomerUpdate) => api.patch<Customer>(`/customers/${id}`, data),
  delete: (id: number) => api.delete<void>(`/customers/${id}`),
}

// ── Suppliers ──────────────────────────────────────────────────────────────

export interface Supplier {
  id: number
  tenant_id: number
  name: string
  address: string | null
  email: string | null
  phone: string | null
  iban: string | null
  default_payment_terms: string | null
  notes: string | null
}

export type SupplierCreate = Omit<Supplier, 'id' | 'tenant_id'>
export type SupplierUpdate = Partial<SupplierCreate>

export const suppliersApi = {
  list: (p: { skip?: number; limit?: number; search?: string } = {}) =>
    api.get<PaginatedResponse<Supplier>>(`/suppliers${listParams(p)}`),
  get: (id: number) => api.get<Supplier>(`/suppliers/${id}`),
  create: (data: SupplierCreate) => api.post<Supplier>('/suppliers', data),
  update: (id: number, data: SupplierUpdate) => api.patch<Supplier>(`/suppliers/${id}`, data),
  delete: (id: number) => api.delete<void>(`/suppliers/${id}`),
}

// ── Materials ──────────────────────────────────────────────────────────────

export interface Material {
  id: number
  tenant_id: number
  sku: string | null
  name: string
  description: string | null
  unit: string
  purchase_price: string | null
  sale_price: string | null
  vat_rate: string
  category: string | null
  default_supplier_id: number | null
  active: boolean
  usage_count: number
}

export type MaterialCreate = Omit<Material, 'id' | 'tenant_id' | 'usage_count'>
export type MaterialUpdate = Partial<MaterialCreate>

export const materialsApi = {
  list: (p: { skip?: number; limit?: number; search?: string; active_only?: boolean } = {}) => {
    const q = new URLSearchParams()
    if (p.skip) q.set('skip', String(p.skip))
    if (p.limit) q.set('limit', String(p.limit))
    if (p.search) q.set('search', p.search)
    if (p.active_only) q.set('active_only', 'true')
    return api.get<PaginatedResponse<Material>>(`/materials${q.toString() ? `?${q}` : ''}`)
  },
  get: (id: number) => api.get<Material>(`/materials/${id}`),
  create: (data: MaterialCreate) => api.post<Material>('/materials', data),
  update: (id: number, data: MaterialUpdate) => api.patch<Material>(`/materials/${id}`, data),
  delete: (id: number) => api.delete<void>(`/materials/${id}`),
}
