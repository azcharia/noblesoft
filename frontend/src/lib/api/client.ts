/**
 * FastAPI Backend Client
 * Automatically attaches Supabase JWT token to all requests
 */
import { env } from '@/lib/env'
import { getSessionToken } from '@/lib/supabase/client'

const API_BASE_URL = env.NEXT_PUBLIC_API_URL
const MAX_AUTH_RETRY_ATTEMPTS = 5

export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message)
    this.name = 'APIError'
  }
}

/**
 * Make authenticated API request
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
  attempt: number = 0
): Promise<T> {
  // Get current session token
  const token = await getSessionToken({
    retries: 2,
    ensureHydrated: true,
    forceRefresh: attempt > 0,
  })
  
  if (!token) {
    if (attempt < MAX_AUTH_RETRY_ATTEMPTS) {
      return apiRequest<T>(endpoint, options, attempt + 1)
    }
    throw new APIError('No authentication token available', 401)
  }
  
  // Build headers
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...options.headers,
  }
  
  // Make request
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })
  
  // Handle errors
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))

    // Handle transient post-login race where first request can see stale/empty token.
    if (response.status === 401 && attempt < MAX_AUTH_RETRY_ATTEMPTS) {
      await getSessionToken({ retries: 2, ensureHydrated: true, forceRefresh: true })
      await new Promise((resolve) => setTimeout(resolve, 600 * (attempt + 1)))
      return apiRequest<T>(endpoint, options, attempt + 1)
    }

    throw new APIError(
      errorData.detail || errorData.message || 'API request failed',
      response.status,
      errorData
    )
  }
  
  // Return JSON response
  return response.json()
}

/**
 * API Client with typed methods
 */
export const apiClient = {
  // Generic methods
  get: <T>(endpoint: string) => apiRequest<T>(endpoint, { method: 'GET' }),
  
  post: <T>(endpoint: string, data?: any) =>
    apiRequest<T>(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  patch: <T>(endpoint: string, data?: any) =>
    apiRequest<T>(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  
  delete: <T>(endpoint: string) =>
    apiRequest<T>(endpoint, { method: 'DELETE' }),
  
  // Products API
  products: {
    list: (params?: {
      page?: number
      page_size?: number
      category?: string
      is_active?: boolean
      search?: string
      low_stock_only?: boolean
    }) => {
      const queryParams = new URLSearchParams()
      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          if (value !== undefined) {
            queryParams.append(key, String(value))
          }
        })
      }
      return apiRequest<ProductListResponse>(
        `/products?${queryParams.toString()}`,
        { method: 'GET' }
      )
    },
    
    get: (id: string) =>
      apiRequest<Product>(`/products/${id}`, { method: 'GET' }),
    
    create: (data: ProductCreate) =>
      apiRequest<Product>('/products', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    
    update: (id: string, data: ProductUpdate) =>
      apiRequest<Product>(`/products/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    
    delete: (id: string) =>
      apiRequest<void>(`/products/${id}`, { method: 'DELETE' }),
    
    adjustStock: (id: string, adjustment: number, reason?: string) =>
      apiRequest<Product>(`/products/${id}/adjust-stock`, {
        method: 'POST',
        body: JSON.stringify({ adjustment, reason }),
      }),
  },
  
  // Invoices API
  invoices: {
    list: (params?: {
      page?: number
      page_size?: number
      payment_status?: string
      customer_name?: string
      overdue_only?: boolean
    }) => {
      const queryParams = new URLSearchParams()
      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          if (value !== undefined) {
            queryParams.append(key, String(value))
          }
        })
      }
      return apiRequest<InvoiceListResponse>(
        `/invoices?${queryParams.toString()}`,
        { method: 'GET' }
      )
    },
    
    get: (id: string) =>
      apiRequest<Invoice>(`/invoices/${id}`, { method: 'GET' }),
    
    create: (data: InvoiceCreate) =>
      apiRequest<Invoice>('/invoices', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    
    update: (id: string, data: InvoiceUpdate) =>
      apiRequest<Invoice>(`/invoices/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    
    updatePaymentStatus: (id: string, status: string, notes?: string) =>
      apiRequest<Invoice>(`/invoices/${id}/payment-status`, {
        method: 'PATCH',
        body: JSON.stringify({ payment_status: status, notes }),
      }),
    
    delete: (id: string) =>
      apiRequest<void>(`/invoices/${id}`, { method: 'DELETE' }),
  },
  
  // AI Chat API
  chat: {
    send: (message: string, conversationHistory?: Array<{ role: string; content: string }>) =>
      apiRequest<ChatResponse>('/chat', {
        method: 'POST',
        body: JSON.stringify({ message, conversation_history: conversationHistory }),
      }),
    
    getSuggestions: () =>
      apiRequest<{ suggestions: string[] }>('/chat/suggestions', { method: 'GET' }),
    
    functionCall: (message: string) =>
      apiRequest<ChatResponse>('/chat/function-call', {
        method: 'POST',
        body: JSON.stringify({ message }),
      }),
  },
}

// Type definitions
export interface Product {
  id: string
  tenant_id: string
  sku: string
  name: string
  description?: string
  category?: string
  unit_price: number
  stock_quantity: number
  low_stock_threshold: number
  is_active: boolean
  is_low_stock: boolean
  created_by?: string
  created_at: string
  updated_at: string
}

export interface ProductCreate {
  sku: string
  name: string
  description?: string
  category?: string
  unit_price: number
  stock_quantity: number
  low_stock_threshold?: number
  is_active?: boolean
}

export interface ProductUpdate {
  sku?: string
  name?: string
  description?: string
  category?: string
  unit_price?: number
  stock_quantity?: number
  low_stock_threshold?: number
  is_active?: boolean
}

export interface ProductListResponse {
  products: Product[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface Invoice {
  id: string
  tenant_id: string
  invoice_number: string
  customer_name: string
  customer_email?: string
  customer_phone?: string
  issue_date: string
  due_date?: string
  subtotal: number
  tax_amount: number
  total_amount: number
  payment_status: 'unpaid' | 'partial' | 'paid' | 'overdue'
  notes?: string
  is_overdue: boolean
  days_until_due?: number
  created_by?: string
  created_at: string
  updated_at: string
  items: InvoiceItem[]
}

export interface InvoiceItem {
  id: string
  invoice_id: string
  product_id?: string
  description: string
  quantity: number
  unit_price: number
  line_total: number
  created_at: string
}

export interface InvoiceCreate {
  invoice_number: string
  customer_name: string
  customer_email?: string
  customer_phone?: string
  issue_date: string
  due_date?: string
  tax_amount?: number
  notes?: string
  items: Array<{
    product_id?: string
    description: string
    quantity: number
    unit_price: number
  }>
}

export interface InvoiceUpdate {
  invoice_number?: string
  customer_name?: string
  customer_email?: string
  customer_phone?: string
  issue_date?: string
  due_date?: string
  payment_status?: string
  notes?: string
  tax_amount?: number
}

export interface InvoiceListResponse {
  invoices: Invoice[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface ChatResponse {
  response: string
  sources: Array<{
    type: string
    content: string
    metadata: Record<string, any>
  }>
  retrieved_count: number
  user_context?: {
    tenant_id: string
    company_name: string
    subscription_tier: string
  }
  assistant_mode?: 'rag' | 'tavily' | 'rag_fallback' | 'hybrid_parallel' | 'function_calling' | string
  orchestration_mode?: 'single' | 'hybrid_parallel' | string
  tool_calls?: Array<{
    id?: string
    type?: string
    name: string
    arguments?: unknown
  }>
  manager_result_summary?: {
    status?: string
    retrieved_count?: number
    source_count?: number
    response_preview?: string
    error?: string
  }
  auditor_result_summary?: {
    status?: string
    tool_count?: number
    source_count?: number
    response_preview?: string
    error?: string
  }
  reconciliation_notes?: string
  error?: string
}
