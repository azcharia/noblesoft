import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { QBRPanel } from './QBRPanel'

const apiMocks = vi.hoisted(() => ({
  getDashboard: vi.fn(),
  createCycle: vi.fn(),
  createGoal: vi.fn(),
  updateGoal: vi.fn(),
}))

vi.mock('@/lib/api/client', () => ({
  apiClient: {
    operations: {
      qbr: {
        getDashboard: apiMocks.getDashboard,
        createCycle: apiMocks.createCycle,
        createGoal: apiMocks.createGoal,
        updateGoal: apiMocks.updateGoal,
      },
    },
  },
}))

const dashboardFixture = {
  cycle: {
    id: 'cycle-1',
    tenant_id: 'tenant-1',
    quarter_code: '2026-Q2',
    title: 'Q2 2026 Review',
    start_date: '2026-04-01',
    end_date: '2026-06-30',
    status: 'active',
    notes: null,
    created_by: 'owner-1',
    created_at: '2026-04-01T08:00:00Z',
    updated_at: '2026-04-01T08:00:00Z',
  },
  goals: [
    {
      id: 'goal-1',
      tenant_id: 'tenant-1',
      cycle_id: 'cycle-1',
      title: 'Increase paid revenue',
      description: 'Target growth to 120M',
      metric_name: 'paid_revenue',
      unit: 'IDR',
      target_value: 120000000,
      current_value: 95000000,
      owner_user_id: 'owner-1',
      status: 'on_track',
      due_date: '2026-06-30',
      created_at: '2026-04-02T08:00:00Z',
      updated_at: '2026-04-05T08:00:00Z',
      progress_percentage: 79.17,
    },
  ],
  metrics: {
    paid_revenue: 95000000,
    unpaid_invoice_count: 11,
    total_products: 125,
    low_stock_products: 14,
  },
}

describe('QBRPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    apiMocks.getDashboard.mockResolvedValue(dashboardFixture)
    apiMocks.createCycle.mockResolvedValue(dashboardFixture.cycle)
    apiMocks.createGoal.mockResolvedValue(dashboardFixture.goals[0])
    apiMocks.updateGoal.mockResolvedValue({
      ...dashboardFixture.goals[0],
      current_value: 100000000,
      progress_percentage: 83.33,
    })
  })

  it('renders qbr dashboard metrics and goals', async () => {
    render(<QBRPanel />)

    await screen.findByText('QBR Dashboard')

    expect(screen.getByText('Paid Revenue')).toBeInTheDocument()
    expect(screen.getByText('Increase paid revenue')).toBeInTheDocument()
    expect(apiMocks.getDashboard).toHaveBeenCalled()
  })

  it('creates qbr cycle and refreshes dashboard', async () => {
    render(<QBRPanel />)

    await screen.findByText('QBR Dashboard')

    await userEvent.type(screen.getByLabelText('Quarter'), '2026-Q3')
    await userEvent.type(screen.getByLabelText('Cycle Title'), 'Q3 2026 Review')
    await userEvent.type(screen.getByLabelText('Start Date'), '2026-07-01')
    await userEvent.type(screen.getByLabelText('End Date'), '2026-09-30')
    await userEvent.click(screen.getByRole('button', { name: 'Buat Cycle' }))

    await waitFor(() => {
      expect(apiMocks.createCycle).toHaveBeenCalledWith({
        quarter_code: '2026-Q3',
        title: 'Q3 2026 Review',
        start_date: '2026-07-01',
        end_date: '2026-09-30',
        status: 'draft',
      })
    })

    await waitFor(() => {
      expect(apiMocks.getDashboard).toHaveBeenCalledTimes(2)
    })
  })

  it('updates goal progress and reloads dashboard', async () => {
    render(<QBRPanel />)

    const updateGoalButton = await screen.findByRole('button', {
      name: 'Update progress goal-1',
    })

    await userEvent.click(updateGoalButton)

    await waitFor(() => {
      expect(apiMocks.updateGoal).toHaveBeenCalledWith('goal-1', {
        current_value: 100000000,
      })
    })

    await waitFor(() => {
      expect(apiMocks.getDashboard).toHaveBeenCalledTimes(2)
    })
  })

  it('creates qbr goal with full fields and refreshes dashboard', async () => {
    render(<QBRPanel />)

    await screen.findByText('QBR Dashboard')

    await userEvent.type(screen.getByLabelText('Title*'), 'Increase Monthly Revenue')
    await userEvent.type(screen.getByLabelText('Description'), 'Target 100M IDR monthly revenue')
    await userEvent.type(screen.getByLabelText('Metric Name'), 'monthly_revenue')
    await userEvent.type(screen.getByLabelText('Unit'), 'IDR')
    await userEvent.type(screen.getByLabelText('Target Value*'), '100000000')
    await userEvent.clear(screen.getByLabelText('Current Value'))
    await userEvent.type(screen.getByLabelText('Current Value'), '15000000')
    await userEvent.selectOptions(screen.getByLabelText('Status'), 'at_risk')
    await userEvent.type(screen.getByLabelText('Due Date'), '2026-06-30')
    await userEvent.type(screen.getByLabelText('Owner User ID'), 'owner-1')
    await userEvent.click(screen.getByRole('button', { name: 'Buat Goal' }))

    await waitFor(() => {
      expect(apiMocks.createGoal).toHaveBeenCalledWith({
        cycle_id: 'cycle-1',
        title: 'Increase Monthly Revenue',
        description: 'Target 100M IDR monthly revenue',
        metric_name: 'monthly_revenue',
        unit: 'IDR',
        target_value: 100000000,
        current_value: 15000000,
        status: 'at_risk',
        due_date: '2026-06-30',
        owner_user_id: 'owner-1',
      })
    })

    await waitFor(() => {
      expect(apiMocks.getDashboard).toHaveBeenCalledTimes(2)
    })
  })

  it('blocks goal submission when target is missing', async () => {
    render(<QBRPanel />)

    await screen.findByText('QBR Dashboard')

    await userEvent.type(screen.getByLabelText('Title*'), 'Incomplete Goal')
    await userEvent.click(screen.getByRole('button', { name: 'Buat Goal' }))

    expect(apiMocks.createGoal).not.toHaveBeenCalled()
  })

  it('shows fallback state when there is no active cycle', async () => {
    apiMocks.getDashboard.mockResolvedValueOnce({
      cycle: null,
      goals: [],
      metrics: {
        paid_revenue: 0,
        unpaid_invoice_count: 0,
        total_products: 0,
        low_stock_products: 0,
      },
    })

    render(<QBRPanel />)

    await screen.findByText('QBR Dashboard')

    expect(screen.getByText('Belum ada cycle aktif')).toBeInTheDocument()
    expect(screen.queryByText('Buat QBR Goal')).not.toBeInTheDocument()
  })

  it('shows not-found error when goal creation fails with 404', async () => {
    apiMocks.createGoal.mockRejectedValueOnce({
      status: 404,
      message: 'not found',
    })

    render(<QBRPanel />)

    await screen.findByText('QBR Dashboard')

    await userEvent.type(screen.getByLabelText('Title*'), 'Increase Revenue')
    await userEvent.type(screen.getByLabelText('Target Value*'), '100000000')
    await userEvent.click(screen.getByRole('button', { name: 'Buat Goal' }))

    expect(await screen.findByText('Cycle atau goal QBR tidak ditemukan.')).toBeInTheDocument()
  })
})
