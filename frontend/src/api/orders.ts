import { api } from './client'

export type OrderStatus = 'open' | 'in_progress' | 'done' | 'cancelled'

export interface Order {
  id: number
  tenant_id: number
  customer_id: number
  quote_id: number | null
  order_no: string
  title: string
  status: OrderStatus
  start_date: string | null
  end_date: string | null
  budget_hours: string | null
  budget_material: string | null
  notes: string | null
  created_at: string
  updated_at: string
  hours_total: number
  hours_billable: number
}

export interface BillableItem {
  id: number
  description: string
  qty: string
  unit: string
  unit_price: string
  line_total: string
  already_invoiced: boolean
  invoice_no: string | null
}

export interface TimeEntry {
  id: number
  order_id: number
  user_id: number
  entry_date: string
  hours: string
  description: string | null
  hourly_rate: string | null
  billable: boolean
  invoiced: boolean
  created_at: string
}

export const STATUS_LABELS: Record<OrderStatus, string> = {
  open: 'Offen', in_progress: 'In Arbeit', done: 'Abgeschlossen', cancelled: 'Storniert',
}
export const STATUS_COLORS: Record<OrderStatus, string> = {
  open: 'info', in_progress: 'warning', done: 'success', cancelled: 'default',
}

function qp(p: Record<string, string | number | undefined>): string {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(p)) if (v !== undefined) q.set(k, String(v))
  return q.toString() ? `?${q}` : ''
}

export const ordersApi = {
  list: (p: { skip?: number; limit?: number; search?: string; status?: string } = {}) =>
    api.get<{ items: Order[]; total: number }>(`/orders${qp(p)}`),
  get: (id: number) => api.get<Order>(`/orders/${id}`),
  create: (data: Partial<Order> & { title: string; customer_id: number }) =>
    api.post<Order>('/orders', data),
  update: (id: number, data: Partial<Order>) => api.patch<Order>(`/orders/${id}`, data),
  delete: (id: number) => api.delete<void>(`/orders/${id}`),
  timeEntries: (orderId: number) => api.get<TimeEntry[]>(`/orders/${orderId}/time`),
  addTime: (orderId: number, data: Partial<TimeEntry> & { entry_date: string; hours: string }) =>
    api.post<TimeEntry>(`/orders/${orderId}/time`, data),
  updateTime: (orderId: number, entryId: number, data: Partial<TimeEntry>) =>
    api.patch<TimeEntry>(`/orders/${orderId}/time/${entryId}`, data),
  deleteTime: (orderId: number, entryId: number) =>
    api.delete<void>(`/orders/${orderId}/time/${entryId}`),
  billableItems: (orderId: number) =>
    api.get<BillableItem[]>(`/orders/${orderId}/billable-items`),
  toInvoice: (orderId: number, data: { invoice_date: string; due_date?: string | null; kind: 'final' | 'partial' | 'advance'; copy_items?: boolean; include_time_entries?: boolean; hourly_rate_default?: string; item_ids?: number[] | null }) =>
    api.post<{ id: number; invoice_no: string }>(`/orders/${orderId}/to-invoice`, data),
}
