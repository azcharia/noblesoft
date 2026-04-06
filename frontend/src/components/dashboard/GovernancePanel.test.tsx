import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GovernancePanel } from '@/components/dashboard/GovernancePanel'

const governanceApiMocks = vi.hoisted(() => ({
  listRoles: vi.fn(),
  createRole: vi.fn(),
  updateRole: vi.fn(),
  deleteRole: vi.fn(),
  listBranches: vi.fn(),
  createBranch: vi.fn(),
  updateBranch: vi.fn(),
  deleteBranch: vi.fn(),
  permissionMatrix: vi.fn(),
  replaceRolePermissions: vi.fn(),
  auditLogs: vi.fn(),
}))

vi.mock('@/lib/api/client', () => ({
  apiClient: {
    governance: {
      roles: {
        list: governanceApiMocks.listRoles,
        create: governanceApiMocks.createRole,
        update: governanceApiMocks.updateRole,
        delete: governanceApiMocks.deleteRole,
      },
      branches: {
        list: governanceApiMocks.listBranches,
        create: governanceApiMocks.createBranch,
        update: governanceApiMocks.updateBranch,
        delete: governanceApiMocks.deleteBranch,
      },
      permissions: {
        matrix: governanceApiMocks.permissionMatrix,
        replaceRolePermissions: governanceApiMocks.replaceRolePermissions,
      },
      auditLogs: {
        list: governanceApiMocks.auditLogs,
      },
    },
  },
}))

describe('GovernancePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    governanceApiMocks.listRoles.mockResolvedValue({
      roles: [
        {
          id: 'role-1',
          tenant_id: 'tenant-1',
          code: 'finance_manager',
          name: 'Finance Manager',
          description: 'Finance approvals',
          is_system: false,
          is_active: true,
          created_at: '2026-03-01T10:00:00Z',
          updated_at: '2026-03-01T10:00:00Z',
        },
        {
          id: 'role-2',
          tenant_id: 'tenant-1',
          code: 'warehouse_lead',
          name: 'Warehouse Lead',
          description: null,
          is_system: false,
          is_active: true,
          created_at: '2026-03-01T10:00:00Z',
          updated_at: '2026-03-01T10:00:00Z',
        },
      ],
      total: 2,
    })

    governanceApiMocks.permissionMatrix.mockResolvedValue({
      roles: [
        {
          role_id: 'role-1',
          role_code: 'finance_manager',
          permission_codes: ['invoices.read'],
        },
        {
          role_id: 'role-2',
          role_code: 'warehouse_lead',
          permission_codes: ['stock.read'],
        },
      ],
      permissions: [
        {
          id: 'perm-1',
          code: 'invoices.read',
          name: 'Read Invoices',
          resource: 'invoices',
          action: 'read',
          description: null,
        },
        {
          id: 'perm-2',
          code: 'invoices.write',
          name: 'Write Invoices',
          resource: 'invoices',
          action: 'write',
          description: null,
        },
        {
          id: 'perm-3',
          code: 'stock.read',
          name: 'Read Stock',
          resource: 'stock',
          action: 'read',
          description: null,
        },
      ],
    })

    governanceApiMocks.listBranches.mockResolvedValue({
      branches: [
        {
          id: 'branch-1',
          tenant_id: 'tenant-1',
          code: 'hq',
          name: 'Headquarters',
          location: 'Jakarta',
          manager_user_id: null,
          is_active: true,
          created_at: '2026-03-01T10:00:00Z',
          updated_at: '2026-03-01T10:00:00Z',
        },
        {
          id: 'branch-2',
          tenant_id: 'tenant-1',
          code: 'west_hub',
          name: 'West Hub',
          location: 'Bandung',
          manager_user_id: null,
          is_active: false,
          created_at: '2026-03-01T10:00:00Z',
          updated_at: '2026-03-01T10:00:00Z',
        },
      ],
      total: 2,
    })

    governanceApiMocks.auditLogs.mockResolvedValue({
      logs: [
        {
          id: 'audit-1',
          tenant_id: 'tenant-1',
          actor_user_id: 'owner-1',
          action: 'update',
          resource_type: 'roles',
          resource_id: 'role-1',
          created_at: '2026-03-01T10:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      page_size: 10,
      has_more: false,
    })

    governanceApiMocks.createRole.mockResolvedValue({ id: 'role-3' })
    governanceApiMocks.updateRole.mockResolvedValue({ id: 'role-1' })
    governanceApiMocks.deleteRole.mockResolvedValue({ role_id: 'role-1', deleted: true })
    governanceApiMocks.createBranch.mockResolvedValue({ id: 'branch-3' })
    governanceApiMocks.updateBranch.mockResolvedValue({ id: 'branch-1' })
    governanceApiMocks.deleteBranch.mockResolvedValue({ branch_id: 'branch-2', deleted: true })
    governanceApiMocks.replaceRolePermissions.mockResolvedValue({
      role_id: 'role-1',
      role_code: 'finance_manager',
      permission_codes: ['invoices.read', 'invoices.write'],
    })
  })

  it('renders governance modules from api responses', async () => {
    render(<GovernancePanel />)

    expect(await screen.findByText('Custom Roles')).toBeInTheDocument()
    expect(screen.getByText('Branches')).toBeInTheDocument()
    expect(screen.getByText('Permission Matrix Editor')).toBeInTheDocument()
    expect(screen.getByText('Recent Audit Logs')).toBeInTheDocument()
    expect(screen.getByText('Headquarters')).toBeInTheDocument()
  })

  it('submits role creation and reloads governance data', async () => {
    render(<GovernancePanel />)

    await screen.findByText('Custom Roles')

    await userEvent.type(screen.getByLabelText('Role code'), 'ops manager')
    await userEvent.type(screen.getByLabelText('Role name'), 'Ops Manager')
    await userEvent.click(screen.getByRole('button', { name: 'Add Role' }))

    await waitFor(() => {
      expect(governanceApiMocks.createRole).toHaveBeenCalledWith({
        code: 'ops_manager',
        name: 'Ops Manager',
      })
    })
  })

  it('edits role and submits update request', async () => {
    render(<GovernancePanel />)

    await screen.findByText('Custom Roles')

    await userEvent.click(screen.getByRole('button', { name: 'Edit role finance_manager' }))
    const input = await screen.findByLabelText('Edit role name')
    await userEvent.clear(input)
    await userEvent.type(input, 'Finance Supervisor')
    await userEvent.click(screen.getByRole('button', { name: 'Save Changes' }))

    await waitFor(() => {
      expect(governanceApiMocks.updateRole).toHaveBeenCalledWith('role-1', {
        name: 'Finance Supervisor',
        description: 'Finance approvals',
      })
    })
  })

  it('deactivates active branch and deletes inactive branch', async () => {
    render(<GovernancePanel />)

    await screen.findByText('Branches')

    await userEvent.click(screen.getByRole('button', { name: 'Deactivate branch hq' }))
    await userEvent.click(screen.getByRole('button', { name: 'Deactivate Branch' }))

    await waitFor(() => {
      expect(governanceApiMocks.updateBranch).toHaveBeenCalledWith('branch-1', {
        is_active: false,
      })
    })

    await userEvent.click(screen.getByRole('button', { name: 'Delete branch west_hub' }))
    await userEvent.click(screen.getByRole('button', { name: 'Delete Permanently' }))

    await waitFor(() => {
      expect(governanceApiMocks.deleteBranch).toHaveBeenCalledWith('branch-2')
    })
  })

  it('applies permission changes with global save', async () => {
    render(<GovernancePanel />)

    await screen.findByText('Permission Matrix Editor')

    await userEvent.click(
      screen.getByLabelText('Toggle invoices.write for role finance_manager')
    )

    await userEvent.click(screen.getByRole('button', { name: 'Save All Changes' }))

    await waitFor(() => {
      expect(governanceApiMocks.replaceRolePermissions).toHaveBeenCalledWith(
        'role-1',
        ['invoices.read', 'invoices.write']
      )
    })
  })
})
