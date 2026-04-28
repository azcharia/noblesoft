import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { OnboardingPanel } from './OnboardingPanel'

const apiMocks = vi.hoisted(() => ({
  list: vi.fn(),
  createItem: vi.fn(),
  updateItem: vi.fn(),
  completeItem: vi.fn(),
}))

vi.mock('@/lib/api/client', () => ({
  apiClient: {
    operations: {
      onboarding: {
        list: apiMocks.list,
        createItem: apiMocks.createItem,
        updateItem: apiMocks.updateItem,
        completeItem: apiMocks.completeItem,
      },
    },
  },
}))

const onboardingFixture = {
  items: [
    {
      id: 'onboard-1',
      tenant_id: 'tenant-1',
      code: 'company_profile',
      title: 'Lengkapi Profil Perusahaan',
      description: 'Isi data legal perusahaan',
      category: 'workspace',
      is_required: true,
      status: 'pending',
      sort_order: 10,
      due_date: null,
      completed_at: null,
      completed_by: null,
      created_at: '2026-04-01T10:00:00Z',
      updated_at: '2026-04-01T10:00:00Z',
    },
  ],
  total: 1,
  completed: 0,
  pending: 1,
  completion_rate: 0,
}

describe('OnboardingPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    apiMocks.list.mockResolvedValue(onboardingFixture)
    apiMocks.createItem.mockResolvedValue({
      ...onboardingFixture.items[0],
      id: 'onboard-2',
      code: 'invite_core_team',
      title: 'Undang Tim Inti',
    })
    apiMocks.updateItem.mockResolvedValue(onboardingFixture.items[0])
    apiMocks.completeItem.mockResolvedValue({
      ...onboardingFixture.items[0],
      status: 'completed',
      completed_at: '2026-04-01T11:00:00Z',
      completed_by: 'owner-1',
    })
  })

  it('renders onboarding summary from API response', async () => {
    render(<OnboardingPanel />)

    await screen.findByText('Onboarding Checklist')

    expect(screen.getByText('Completion Rate')).toBeInTheDocument()
    expect(screen.getByText('0%')).toBeInTheDocument()
    expect(screen.getByText('Lengkapi Profil Perusahaan')).toBeInTheDocument()
    expect(apiMocks.list).toHaveBeenCalled()
  })

  it('creates onboarding item and reloads checklist', async () => {
    render(<OnboardingPanel />)

    await screen.findByText('Onboarding Checklist')

    await userEvent.type(screen.getByLabelText('Kode Task'), 'invite_core_team')
    await userEvent.type(screen.getByLabelText('Judul Task'), 'Undang Tim Inti')
    await userEvent.click(screen.getByRole('button', { name: 'Tambah Task' }))

    await waitFor(() => {
      expect(apiMocks.createItem).toHaveBeenCalledWith({
        code: 'invite_core_team',
        title: 'Undang Tim Inti',
        category: 'workspace',
        is_required: true,
      })
    })

    await waitFor(() => {
      expect(apiMocks.list).toHaveBeenCalledTimes(2)
    })
  })

  it('completes onboarding item and refreshes summary', async () => {
    render(<OnboardingPanel />)

    const completeButton = await screen.findByRole('button', {
      name: 'Tandai selesai company_profile',
    })

    await userEvent.click(completeButton)

    await waitFor(() => {
      expect(apiMocks.completeItem).toHaveBeenCalledWith('onboard-1')
    })

    await waitFor(() => {
      expect(apiMocks.list).toHaveBeenCalledTimes(2)
    })
  })

  it('edits onboarding item and sends full update payload', async () => {
    render(<OnboardingPanel />)

    const editButton = await screen.findByRole('button', {
      name: 'Edit company_profile',
    })
    await userEvent.click(editButton)

    await screen.findByText('Edit Task: company_profile')
    await userEvent.clear(screen.getByLabelText('Title'))
    await userEvent.type(screen.getByLabelText('Title'), 'Lengkapi Profil Terbaru')
    await userEvent.clear(screen.getByLabelText('Description'))
    await userEvent.type(screen.getByLabelText('Description'), 'Perbarui data legal 2026')
    await userEvent.clear(screen.getByLabelText('Category'))
    await userEvent.type(screen.getByLabelText('Category'), 'compliance')
    await userEvent.selectOptions(screen.getByLabelText('Status'), 'in_progress')
    await userEvent.type(screen.getByLabelText('Due Date'), '2026-05-01')
    await userEvent.click(screen.getByRole('checkbox', { name: 'Is Required' }))
    await userEvent.click(screen.getByRole('button', { name: 'Update Task' }))

    await waitFor(() => {
      expect(apiMocks.updateItem).toHaveBeenCalledWith('onboard-1', {
        title: 'Lengkapi Profil Terbaru',
        description: 'Perbarui data legal 2026',
        category: 'compliance',
        status: 'in_progress',
        due_date: '2026-05-01',
        is_required: false,
      })
    })

    await waitFor(() => {
      expect(apiMocks.list).toHaveBeenCalledTimes(2)
    })
  })

  it('shows not-found error when update item fails with 404', async () => {
    apiMocks.updateItem.mockRejectedValueOnce({
      status: 404,
      message: 'not found',
    })

    render(<OnboardingPanel />)

    const editButton = await screen.findByRole('button', {
      name: 'Edit company_profile',
    })
    await userEvent.click(editButton)

    await screen.findByText('Edit Task: company_profile')
    await userEvent.click(screen.getByRole('button', { name: 'Update Task' }))

    expect(await screen.findByText('Task onboarding tidak ditemukan atau sudah berubah.')).toBeInTheDocument()
  })
})
