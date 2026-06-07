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
      apiRequest<Product>('/products/', {
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

  // Billing API
  billing: {
    getCatalog: () =>
      apiRequest<BillingCatalogResponse>('/billing/catalog', { method: 'GET' }),

    getStatus: () =>
      apiRequest<BillingStatusResponse>('/billing/status', { method: 'GET' }),

    createTransaction: (data: BillingTransactionPayload) =>
      apiRequest<BillingTransactionResponse>('/billing/midtrans/transaction', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  // Tenant Users API
  users: {
    list: (includeInactive: boolean = false) =>
      apiRequest<TenantUsersListResponse>(
        `/users?${new URLSearchParams({ include_inactive: String(includeInactive) }).toString()}`,
        { method: 'GET' }
      ),

    invite: (data: TenantUserInviteRequest) =>
      apiRequest<TenantUserInviteResponse>('/users/invite', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    deactivate: (userId: string) =>
      apiRequest<TenantUserDeactivateResponse>(`/users/${encodeURIComponent(userId)}`, { method: 'DELETE' }),

    reactivate: (userId: string) =>
      apiRequest<TenantUserReactivateResponse>(`/users/${encodeURIComponent(userId)}/reactivate`, {
        method: 'POST',
      }),
  },

  // Governance API
  governance: {
    roles: {
      list: (includeInactive: boolean = false) =>
        apiRequest<GovernanceRoleListResponse>(
          `/governance/roles?${new URLSearchParams({ include_inactive: String(includeInactive) }).toString()}`,
          { method: 'GET' }
        ),

      create: (data: GovernanceRoleCreateRequest) =>
        apiRequest<GovernanceRole>('/governance/roles', {
          method: 'POST',
          body: JSON.stringify(data),
        }),

      update: (roleId: string, data: GovernanceRoleUpdateRequest) =>
        apiRequest<GovernanceRole>(`/governance/roles/${encodeURIComponent(roleId)}`, {
          method: 'PATCH',
          body: JSON.stringify(data),
        }),

      delete: (roleId: string) =>
        apiRequest<GovernanceRoleDeleteResponse>(`/governance/roles/${encodeURIComponent(roleId)}`, {
          method: 'DELETE',
        }),
    },

    permissions: {
      list: () =>
        apiRequest<GovernancePermission[]>('/governance/permissions', { method: 'GET' }),

      matrix: (includeInactiveRoles: boolean = false) =>
        apiRequest<GovernancePermissionMatrixResponse>(
          `/governance/permissions/matrix?${new URLSearchParams({ include_inactive_roles: String(includeInactiveRoles) }).toString()}`,
          { method: 'GET' }
        ),

      replaceRolePermissions: (roleId: string, permissionCodes: string[]) =>
        apiRequest<GovernanceRolePermissionRow>(`/governance/roles/${encodeURIComponent(roleId)}/permissions`, {
          method: 'PUT',
          body: JSON.stringify({ permission_codes: permissionCodes }),
        }),
    },

    branches: {
      list: (includeInactive: boolean = false) =>
        apiRequest<GovernanceBranchListResponse>(
          `/governance/branches?${new URLSearchParams({ include_inactive: String(includeInactive) }).toString()}`,
          { method: 'GET' }
        ),

      create: (data: GovernanceBranchCreateRequest) =>
        apiRequest<GovernanceBranch>('/governance/branches', {
          method: 'POST',
          body: JSON.stringify(data),
        }),

      update: (branchId: string, data: GovernanceBranchUpdateRequest) =>
        apiRequest<GovernanceBranch>(`/governance/branches/${encodeURIComponent(branchId)}`, {
          method: 'PATCH',
          body: JSON.stringify(data),
        }),

      delete: (branchId: string) =>
        apiRequest<GovernanceBranchDeleteResponse>(`/governance/branches/${encodeURIComponent(branchId)}`, {
          method: 'DELETE',
        }),

      assignUser: (data: GovernanceBranchAssignRequest) =>
        apiRequest<GovernanceBranchAssignResponse>('/governance/branches/assign', {
          method: 'POST',
          body: JSON.stringify(data),
        }),
    },

    auditLogs: {
      list: (params?: {
        page?: number
        page_size?: number
        action?: string
        resource_type?: string
      }) => {
        const queryParams = new URLSearchParams()
        if (params) {
          Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
              queryParams.append(key, String(value))
            }
          })
        }
        return apiRequest<GovernanceAuditLogListResponse>(
          `/governance/audit-logs?${queryParams.toString()}`,
          { method: 'GET' }
        )
      },
    },
  },

  // Operations API
  operations: {
    onboarding: {
      list: () =>
        apiRequest<OnboardingChecklistResponse>('/operations/onboarding', { method: 'GET' }),

      createItem: (data: OnboardingItemCreateRequest) =>
        apiRequest<OnboardingItem>('/operations/onboarding/items', {
          method: 'POST',
          body: JSON.stringify(data),
        }),

      updateItem: (itemId: string, data: OnboardingItemUpdateRequest) =>
        apiRequest<OnboardingItem>(`/operations/onboarding/items/${encodeURIComponent(itemId)}`, {
          method: 'PATCH',
          body: JSON.stringify(data),
        }),

      completeItem: (itemId: string) =>
        apiRequest<OnboardingItem>(`/operations/onboarding/items/${encodeURIComponent(itemId)}/complete`, {
          method: 'POST',
        }),
    },

    support: {
      listTickets: (params?: {
        page?: number
        page_size?: number
        status?: string
        priority?: string
      }) => {
        const queryParams = new URLSearchParams()
        if (params) {
          Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
              queryParams.append(key, String(value))
            }
          })
        }
        return apiRequest<SupportTicketListResponse>(
          `/operations/support/tickets?${queryParams.toString()}`,
          { method: 'GET' }
        )
      },

      getTicket: (ticketId: string) =>
        apiRequest<SupportTicketDetailResponse>(`/operations/support/tickets/${encodeURIComponent(ticketId)}`, {
          method: 'GET',
        }),

      createTicket: (data: SupportTicketCreateRequest) =>
        apiRequest<SupportTicket>('/operations/support/tickets', {
          method: 'POST',
          body: JSON.stringify(data),
        }),

      updateTicket: (ticketId: string, data: SupportTicketUpdateRequest) =>
        apiRequest<SupportTicket>(`/operations/support/tickets/${encodeURIComponent(ticketId)}`, {
          method: 'PATCH',
          body: JSON.stringify(data),
        }),

      assignTicket: (ticketId: string, data: SupportTicketAssignRequest) =>
        apiRequest<SupportTicket>(`/operations/support/tickets/${encodeURIComponent(ticketId)}/assignee`, {
          method: 'PATCH',
          body: JSON.stringify(data),
        }),

      addComment: (ticketId: string, data: SupportTicketCommentCreateRequest) =>
        apiRequest<SupportTicketComment>(`/operations/support/tickets/${encodeURIComponent(ticketId)}/comments`, {
          method: 'POST',
          body: JSON.stringify(data),
        }),

      getOverview: () =>
        apiRequest<SupportOverviewResponse>('/operations/support/overview', { method: 'GET' }),
    },

    qbr: {
      listCycles: (params?: {
        page?: number
        page_size?: number
        status?: string
      }) => {
        const queryParams = new URLSearchParams()
        if (params) {
          Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
              queryParams.append(key, String(value))
            }
          })
        }
        return apiRequest<QBRCycleListResponse>(
          `/operations/qbr/cycles?${queryParams.toString()}`,
          { method: 'GET' }
        )
      },

      createCycle: (data: QBRCycleCreateRequest) =>
        apiRequest<QBRCycle>('/operations/qbr/cycles', {
          method: 'POST',
          body: JSON.stringify(data),
        }),

      updateCycle: (cycleId: string, data: QBRCycleUpdateRequest) =>
        apiRequest<QBRCycle>(`/operations/qbr/cycles/${encodeURIComponent(cycleId)}`, {
          method: 'PATCH',
          body: JSON.stringify(data),
        }),

      listGoals: (params?: {
        cycle_id?: string
        page?: number
        page_size?: number
      }) => {
        const queryParams = new URLSearchParams()
        if (params) {
          Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
              queryParams.append(key, String(value))
            }
          })
        }
        return apiRequest<QBRGoalListResponse>(
          `/operations/qbr/goals?${queryParams.toString()}`,
          { method: 'GET' }
        )
      },

      createGoal: (data: QBRGoalCreateRequest) =>
        apiRequest<QBRGoal>('/operations/qbr/goals', {
          method: 'POST',
          body: JSON.stringify(data),
        }),

      updateGoal: (goalId: string, data: QBRGoalUpdateRequest) =>
        apiRequest<QBRGoal>(`/operations/qbr/goals/${encodeURIComponent(goalId)}`, {
          method: 'PATCH',
          body: JSON.stringify(data),
        }),

      getDashboard: (cycleId?: string) => {
        const query = cycleId
          ? `?${new URLSearchParams({ cycle_id: cycleId }).toString()}`
          : ''
        return apiRequest<QBRDashboardResponse>(`/operations/qbr/dashboard${query}`, {
          method: 'GET',
        })
      },
    },
  },
  
  // AI Chat API
  chat: {
    send: (message: string, conversationHistory?: Array<{ role: string; content: string }>) =>
      apiRequest<ChatResponse>('/chat', {
        method: 'POST',
        body: JSON.stringify({ message, conversation_history: conversationHistory }),
      }),
    
    confirm: (pendingAction: any) =>
      apiRequest<ChatResponse>('/chat/confirm', {
        method: 'POST',
        body: JSON.stringify(pendingAction),
      }),
    
    getSuggestions: () =>
      apiRequest<{ suggestions: string[] }>('/chat/suggestions', { method: 'GET' }),
    
    transcribe: async (audioBlob: Blob) => {
      const formData = new FormData()
      formData.append('file', audioBlob, 'recording.webm')
      
      const token = await getSessionToken({ retries: 2, ensureHydrated: true })
      
      const response = await fetch(`${API_BASE_URL}/chat/transcribe`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new APIError(
          errorData.detail || 'Gagal mengirim file suara',
          response.status
        )
      }
      
      return response.json() as Promise<{ text: string; language: string }>
    },
    
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

export type TenantUserRole = string

export interface TenantUser {
  id: string
  tenant_id: string
  email: string
  full_name?: string | null
  role: TenantUserRole
  role_id?: string | null
  branch_id?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TenantUsersListResponse {
  users: TenantUser[]
  total: number
}

export interface TenantUserInviteRequest {
  email: string
  full_name?: string
  role?: TenantUserRole
  temp_password?: string
  auto_confirm_email?: boolean
  include_temporary_password?: boolean
}

export interface TenantUserInviteResponse {
  user: TenantUser
  temporary_password?: string | null
}

export interface TenantUserDeactivateResponse {
  user_id: string
  deactivated: boolean
}

export interface TenantUserReactivateResponse {
  user_id: string
  reactivated: boolean
}

export interface GovernanceRole {
  id: string
  tenant_id: string
  code: string
  name: string
  description?: string | null
  is_system: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface GovernanceRoleListResponse {
  roles: GovernanceRole[]
  total: number
}

export interface GovernanceRoleCreateRequest {
  code: string
  name: string
  description?: string
  copy_from_role_id?: string
}

export interface GovernanceRoleUpdateRequest {
  name?: string
  description?: string
  is_active?: boolean
}

export interface GovernanceRoleDeleteResponse {
  role_id: string
  deleted: boolean
}

export interface GovernancePermission {
  id: string
  code: string
  name: string
  resource: string
  action: string
  description?: string | null
}

export interface GovernanceRolePermissionRow {
  role_id: string
  role_code: string
  permission_codes: string[]
}

export interface GovernancePermissionMatrixResponse {
  roles: GovernanceRolePermissionRow[]
  permissions: GovernancePermission[]
}

export interface GovernanceBranch {
  id: string
  tenant_id: string
  code: string
  name: string
  location?: string | null
  manager_user_id?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface GovernanceBranchListResponse {
  branches: GovernanceBranch[]
  total: number
}

export interface GovernanceBranchCreateRequest {
  code: string
  name: string
  location?: string
  manager_user_id?: string
}

export interface GovernanceBranchUpdateRequest {
  name?: string
  location?: string
  manager_user_id?: string
  is_active?: boolean
}

export interface GovernanceBranchAssignRequest {
  user_id: string
  branch_id: string
}

export interface GovernanceBranchAssignResponse {
  user_id: string
  branch_id: string
  updated: boolean
}

export interface GovernanceBranchDeleteResponse {
  branch_id: string
  deleted: boolean
}

export interface GovernanceAuditLogEntry {
  id: string
  tenant_id: string
  actor_user_id?: string | null
  action: string
  resource_type: string
  resource_id?: string | null
  old_values?: Record<string, any> | null
  new_values?: Record<string, any> | null
  metadata?: Record<string, any>
  created_at: string
}

export interface GovernanceAuditLogListResponse {
  logs: GovernanceAuditLogEntry[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export type OnboardingStatus = 'pending' | 'in_progress' | 'completed' | 'skipped'

export interface OnboardingItem {
  id: string
  tenant_id: string
  code: string
  title: string
  description?: string | null
  category: string
  is_required: boolean
  status: OnboardingStatus
  sort_order: number
  due_date?: string | null
  completed_at?: string | null
  completed_by?: string | null
  created_at: string
  updated_at: string
}

export interface OnboardingChecklistResponse {
  items: OnboardingItem[]
  total: number
  completed: number
  pending: number
  completion_rate: number
}

export interface OnboardingItemCreateRequest {
  code: string
  title: string
  description?: string
  category?: string
  is_required?: boolean
  status?: OnboardingStatus
  sort_order?: number
  due_date?: string
}

export interface OnboardingItemUpdateRequest {
  title?: string
  description?: string
  category?: string
  is_required?: boolean
  status?: OnboardingStatus
  sort_order?: number
  due_date?: string
}

export type SupportPriority = 'p1' | 'p2' | 'p3'
export type SupportTicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed'

export interface SupportTicket {
  id: string
  tenant_id: string
  ticket_number: string
  title: string
  description?: string | null
  category: string
  priority: SupportPriority
  status: SupportTicketStatus
  requester_user_id?: string | null
  assignee_user_id?: string | null
  first_response_at?: string | null
  resolved_at?: string | null
  sla_response_deadline: string
  sla_resolution_deadline: string
  is_sla_response_breached: boolean
  is_sla_resolution_breached: boolean
  created_at: string
  updated_at: string
}

export interface SupportTicketListResponse {
  tickets: SupportTicket[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface SupportTicketCreateRequest {
  title: string
  description?: string
  category?: string
  priority?: SupportPriority
  assignee_user_id?: string
}

export interface SupportTicketUpdateRequest {
  title?: string
  description?: string
  category?: string
  priority?: SupportPriority
  status?: SupportTicketStatus
  assignee_user_id?: string
}

export interface SupportTicketAssignRequest {
  assignee_user_id: string
}

export interface SupportTicketCommentCreateRequest {
  content: string
  is_internal?: boolean
}

export interface SupportTicketComment {
  id: string
  tenant_id: string
  ticket_id: string
  author_user_id?: string | null
  content: string
  is_internal: boolean
  created_at: string
}

export interface SupportTicketDetailResponse {
  ticket: SupportTicket
  comments: SupportTicketComment[]
}

export interface SupportOverviewResponse {
  total_open: number
  total_in_progress: number
  total_resolved: number
  total_closed: number
  sla_response_breached: number
  sla_resolution_breached: number
}

export type QBRCycleStatus = 'draft' | 'active' | 'completed'
export type QBRGoalStatus = 'on_track' | 'at_risk' | 'off_track' | 'achieved'

export interface QBRCycle {
  id: string
  tenant_id: string
  quarter_code: string
  title?: string | null
  start_date: string
  end_date: string
  status: QBRCycleStatus
  notes?: string | null
  created_by?: string | null
  created_at: string
  updated_at: string
}

export interface QBRCycleListResponse {
  cycles: QBRCycle[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface QBRCycleCreateRequest {
  quarter_code: string
  title?: string
  start_date: string
  end_date: string
  status?: QBRCycleStatus
  notes?: string
}

export interface QBRCycleUpdateRequest {
  title?: string
  start_date?: string
  end_date?: string
  status?: QBRCycleStatus
  notes?: string
}

export interface QBRGoal {
  id: string
  tenant_id: string
  cycle_id: string
  title: string
  description?: string | null
  metric_name?: string | null
  unit?: string | null
  target_value: number
  current_value: number
  owner_user_id?: string | null
  status: QBRGoalStatus
  due_date?: string | null
  created_at: string
  updated_at: string
  progress_percentage: number
}

export interface QBRGoalListResponse {
  goals: QBRGoal[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface QBRGoalCreateRequest {
  cycle_id: string
  title: string
  description?: string
  metric_name?: string
  unit?: string
  target_value?: number
  current_value?: number
  owner_user_id?: string
  status?: QBRGoalStatus
  due_date?: string
}

export interface QBRGoalUpdateRequest {
  cycle_id?: string
  title?: string
  description?: string
  metric_name?: string
  unit?: string
  target_value?: number
  current_value?: number
  owner_user_id?: string
  status?: QBRGoalStatus
  due_date?: string
}

export interface QBRMetricsSummary {
  paid_revenue: number
  unpaid_invoice_count: number
  total_products: number
  low_stock_products: number
}

export interface QBRDashboardResponse {
  cycle?: QBRCycle | null
  goals: QBRGoal[]
  metrics: QBRMetricsSummary
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
  function_executed?: string
  execution_result?: Record<string, any>
}

export type BillingTier = 'basic' | 'pro' | 'enterprise'
export type BillingPeriod = 'monthly' | 'annual'
export type BillingAddOnCode = 'ai_agent_pack' | 'automation_pack'

export interface BillingAddOnSelection {
  code: BillingAddOnCode
  quantity: number
}

export interface BillingStatusResponse {
  tenant_id: string
  company_name: string
  subscription_tier: string
  is_active: boolean
  max_users: number
  payment_gateway_customer_id?: string | null
  billing_period?: BillingPeriod
  add_ons?: BillingAddOnSelection[]
  billing_start_date?: string | null
  billing_end_date?: string | null
}

export interface BillingCatalogPlan {
  tier: BillingTier
  monthly_price: number | string
  annual_price: number | string
  annual_discount_percent: number
  max_users: number
}

export interface BillingCatalogAddOn {
  code: BillingAddOnCode
  name: string
  description: string
  monthly_price: number | string
  annual_price: number | string
}

export interface BillingCatalogResponse {
  currency: string
  annual_discount_percent: number
  plans: BillingCatalogPlan[]
  add_ons: BillingCatalogAddOn[]
}

export interface BillingTransactionPayload {
  target_tier: BillingTier
  billing_period: BillingPeriod
  add_ons?: BillingAddOnSelection[]
  customer_name?: string
  customer_email?: string
  customer_phone?: string
  notes?: string
}

export interface BillingTransactionLineItem {
  id: string
  name: string
  price: number | string
  quantity: number
  subtotal: number | string
}

export interface BillingTransactionResponse {
  order_id: string
  token: string
  redirect_url: string
  target_tier: BillingTier
  amount: number | string
  billing_period: BillingPeriod
  line_items: BillingTransactionLineItem[]
}
