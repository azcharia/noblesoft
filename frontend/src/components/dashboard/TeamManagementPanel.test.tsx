import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { TeamManagementPanel } from '@/components/dashboard/TeamManagementPanel'

const apiMocks = vi.hoisted(() => ({
  listUsers: vi.fn(),
  getBillingStatus: vi.fn(),
  deactivateUser: vi.fn(),
  reactivateUser: vi.fn(),
  inviteUser: vi.fn(),
}))

vi.mock('@/lib/api/client', () => ({
  apiClient: {
    users: {
      list: apiMocks.listUsers,
      invite: apiMocks.inviteUser,
      deactivate: apiMocks.deactivateUser,
      reactivate: apiMocks.reactivateUser,
    },
    billing: {
      getStatus: apiMocks.getBillingStatus,
    },
  },
}))

const fixtureUsers = [
  {
    id: 'owner-1',
    tenant_id: 'tenant-1',
    email: 'owner@noblesoft.test',
    full_name: 'Owner User',
    role: 'owner',
    is_active: true,
    created_at: '2026-03-01T10:00:00Z',
    updated_at: '2026-03-01T10:00:00Z',
  },
  {
    id: 'member-1',
    tenant_id: 'tenant-1',
    email: 'member@noblesoft.test',
    full_name: 'Member Active',
    role: 'member',
    is_active: true,
    created_at: '2026-03-01T10:00:00Z',
    updated_at: '2026-03-01T10:00:00Z',
  },
  {
    id: 'member-2',
    tenant_id: 'tenant-1',
    email: 'archived@noblesoft.test',
    full_name: 'Member Inactive',
    role: 'member',
    is_active: false,
    created_at: '2026-03-01T10:00:00Z',
    updated_at: '2026-03-01T10:00:00Z',
  },
]

const billingStatus = {
  tenant_id: 'tenant-1',
  company_name: 'NobleSoft',
  subscription_tier: 'pro',
  is_active: true,
  max_users: 5,
  payment_gateway_customer_id: null,
}

describe('TeamManagementPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    apiMocks.listUsers.mockResolvedValue({
      users: fixtureUsers,
      total: fixtureUsers.length,
    })
    apiMocks.getBillingStatus.mockResolvedValue(billingStatus)
    apiMocks.deactivateUser.mockResolvedValue({ user_id: 'member-1', deactivated: true })
    apiMocks.reactivateUser.mockResolvedValue({ user_id: 'member-2', reactivated: true })
    apiMocks.inviteUser.mockResolvedValue({
      user: {
        id: 'member-3',
        tenant_id: 'tenant-1',
        email: 'new@noblesoft.test',
        full_name: 'New Member',
        role: 'member',
        is_active: true,
        created_at: '2026-03-01T10:00:00Z',
        updated_at: '2026-03-01T10:00:00Z',
      },
      temporary_password: 'temp-pass-123',
    })
  })

  it('renders seat usage summary from API responses', async () => {
    render(<TeamManagementPanel currentUserId="owner-1" currentUserRole="owner" />)

    await screen.findByText('Team Members')

    expect(screen.getByText('Active Seats')).toBeInTheDocument()
    expect(screen.getByText('Available Seats')).toBeInTheDocument()
    expect(screen.getByText('Total Members')).toBeInTheDocument()
    expect(screen.getByText('of 5 seats')).toBeInTheDocument()
  })

  it('calls deactivate endpoint and reloads users list', async () => {
    render(<TeamManagementPanel currentUserId="owner-1" currentUserRole="owner" />)

    const deactivateButton = await screen.findByRole('button', {
      name: 'Deactivate member@noblesoft.test',
    })

    await userEvent.click(deactivateButton)

    await waitFor(() => {
      expect(apiMocks.deactivateUser).toHaveBeenCalledWith('member-1')
    })
    await waitFor(() => {
      expect(apiMocks.listUsers).toHaveBeenCalledTimes(2)
    })
  })

  it('shows seat-limit error on reactivate when API returns 400', async () => {
    apiMocks.reactivateUser.mockRejectedValue(
      Object.assign(new Error('Tenant user limit has been reached'), { status: 400 })
    )

    render(<TeamManagementPanel currentUserId="owner-1" currentUserRole="owner" />)

    const reactivateButton = await screen.findByRole('button', {
      name: 'Reactivate archived@noblesoft.test',
    })

    await userEvent.click(reactivateButton)

    await waitFor(() => {
      expect(screen.getByText('Seat user sudah penuh. Nonaktifkan user lain terlebih dahulu.')).toBeInTheDocument()
    })
  })

  it('disables self deactivation action', async () => {
    render(<TeamManagementPanel currentUserId="owner-1" currentUserRole="owner" />)

    const selfDeactivateButton = await screen.findByRole('button', {
      name: 'Deactivate owner@noblesoft.test',
    })

    expect(selfDeactivateButton).toBeDisabled()
  })

  it('submits invite with simple payload and refetches users', async () => {
    render(<TeamManagementPanel currentUserId="owner-1" currentUserRole="owner" />)

    await screen.findByText('Team Members')

    await userEvent.click(screen.getByRole('button', { name: 'Invite' }))
    await userEvent.type(screen.getByLabelText('Email'), 'new@noblesoft.test')
    await userEvent.type(screen.getByLabelText('Nama Lengkap'), 'New Member')
    await userEvent.click(screen.getByRole('button', { name: 'Invite Member' }))

    await waitFor(() => {
      expect(apiMocks.inviteUser).toHaveBeenCalledWith({
        email: 'new@noblesoft.test',
        full_name: 'New Member',
        role: 'member',
        include_temporary_password: true,
      })
    })

    await waitFor(() => {
      expect(apiMocks.listUsers).toHaveBeenCalledTimes(2)
    })

    expect(await screen.findByText('Undangan Berhasil Dibuat')).toBeInTheDocument()
    expect(screen.getByText('temp-pass-123')).toBeInTheDocument()
  })

  it('copies temporary password after successful invite', async () => {
    const clipboardSpy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined)

    render(<TeamManagementPanel currentUserId="owner-1" currentUserRole="owner" />)

    await screen.findByText('Team Members')

    await userEvent.click(screen.getByRole('button', { name: 'Invite' }))
    await userEvent.type(screen.getByLabelText('Email'), 'new@noblesoft.test')
    await userEvent.type(screen.getByLabelText('Nama Lengkap'), 'New Member')
    await userEvent.click(screen.getByRole('button', { name: 'Invite Member' }))

    await screen.findByText('temp-pass-123')

    await userEvent.click(screen.getByRole('button', { name: 'Copy' }))

    await waitFor(() => {
      expect(clipboardSpy).toHaveBeenCalledWith('temp-pass-123')
    })
    expect(screen.getByRole('button', { name: 'Copied' })).toBeInTheDocument()
  })

  it('clears temporary password when invite dialog is closed', async () => {
    render(<TeamManagementPanel currentUserId="owner-1" currentUserRole="owner" />)

    await screen.findByText('Team Members')

    await userEvent.click(screen.getByRole('button', { name: 'Invite' }))
    await userEvent.type(screen.getByLabelText('Email'), 'new@noblesoft.test')
    await userEvent.type(screen.getByLabelText('Nama Lengkap'), 'New Member')
    await userEvent.click(screen.getByRole('button', { name: 'Invite Member' }))

    await screen.findByText('temp-pass-123')

    await userEvent.click(screen.getByRole('button', { name: 'Close invite modal' }))

    await userEvent.click(screen.getByRole('button', { name: 'Invite' }))

    expect(screen.queryByText('temp-pass-123')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
  })

  it('surfaces duplicate email error from invite API', async () => {
    apiMocks.inviteUser.mockRejectedValue(
      Object.assign(new Error("User with email 'new@noblesoft.test' already exists"), { status: 400 })
    )

    render(<TeamManagementPanel currentUserId="owner-1" currentUserRole="owner" />)

    await screen.findByText('Team Members')

    await userEvent.click(screen.getByRole('button', { name: 'Invite' }))
    await userEvent.type(screen.getByLabelText('Email'), 'new@noblesoft.test')
    await userEvent.type(screen.getByLabelText('Nama Lengkap'), 'New Member')
    await userEvent.click(screen.getByRole('button', { name: 'Invite Member' }))

    await waitFor(() => {
      expect(screen.getByText('Email sudah terdaftar pada tenant ini.')).toBeInTheDocument()
    })
  })
})
