import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SupportPanel } from './SupportPanel'

const apiMocks = vi.hoisted(() => ({
  listTickets: vi.fn(),
  createTicket: vi.fn(),
  updateTicket: vi.fn(),
  getOverview: vi.fn(),
  getTicket: vi.fn(),
  addComment: vi.fn(),
  assignTicket: vi.fn(),
}))

vi.mock('@/lib/api/client', () => ({
  apiClient: {
    operations: {
      support: {
        listTickets: apiMocks.listTickets,
        createTicket: apiMocks.createTicket,
        updateTicket: apiMocks.updateTicket,
        getOverview: apiMocks.getOverview,
        getTicket: apiMocks.getTicket,
        addComment: apiMocks.addComment,
        assignTicket: apiMocks.assignTicket,
      },
    },
  },
}))

const ticketFixture = {
  tickets: [
    {
      id: 'ticket-1',
      tenant_id: 'tenant-1',
      ticket_number: 'SUP-20260406-0001',
      title: 'Payment webhook delayed',
      description: 'Need investigation',
      category: 'billing',
      priority: 'p1',
      status: 'open',
      requester_user_id: 'owner-1',
      assignee_user_id: null,
      first_response_at: null,
      resolved_at: null,
      sla_response_deadline: '2026-04-06T09:00:00Z',
      sla_resolution_deadline: '2026-04-06T16:00:00Z',
      is_sla_response_breached: false,
      is_sla_resolution_breached: false,
      created_at: '2026-04-06T08:00:00Z',
      updated_at: '2026-04-06T08:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
  has_more: false,
}

const overviewFixture = {
  total_open: 1,
  total_in_progress: 0,
  total_resolved: 0,
  total_closed: 0,
  sla_response_breached: 0,
  sla_resolution_breached: 0,
}

const ticketDetailFixture = {
  ticket: {
    ...ticketFixture.tickets[0],
    assignee_user_id: 'user-123',
  },
  comments: [
    {
      id: 'comment-1',
      tenant_id: 'tenant-1',
      ticket_id: 'ticket-1',
      author_user_id: 'owner-1',
      content: 'Initial triage complete',
      is_internal: true,
      created_at: '2026-04-06T09:00:00Z',
    },
  ],
}

describe('SupportPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    apiMocks.listTickets.mockResolvedValue(ticketFixture)
    apiMocks.getOverview.mockResolvedValue(overviewFixture)
    apiMocks.createTicket.mockResolvedValue(ticketFixture.tickets[0])
    apiMocks.updateTicket.mockResolvedValue({
      ...ticketFixture.tickets[0],
      status: 'in_progress',
      first_response_at: '2026-04-06T08:20:00Z',
    })
    apiMocks.getTicket.mockResolvedValue(ticketDetailFixture)
    apiMocks.addComment.mockResolvedValue(ticketDetailFixture.comments[0])
    apiMocks.assignTicket.mockResolvedValue({
      ...ticketFixture.tickets[0],
      assignee_user_id: 'user-999',
    })
  })

  it('renders support ticket list and overview cards', async () => {
    render(<SupportPanel />)

    await screen.findByText('Support Ticketing')

    expect(screen.getByText('Open Tickets')).toBeInTheDocument()
    expect(screen.getByText('Payment webhook delayed')).toBeInTheDocument()
    expect(apiMocks.listTickets).toHaveBeenCalled()
    expect(apiMocks.getOverview).toHaveBeenCalled()
  })

  it('creates ticket and refreshes ticket feed', async () => {
    render(<SupportPanel />)

    await screen.findByText('Support Ticketing')

    await userEvent.type(screen.getByLabelText('Judul Ticket'), 'Inventory sync issue')
    await userEvent.type(screen.getByLabelText('Deskripsi Ticket'), 'Stock sync failed for branch hq')
    await userEvent.selectOptions(screen.getByLabelText('Priority'), 'p2')
    await userEvent.click(screen.getByRole('button', { name: 'Buat Ticket' }))

    await waitFor(() => {
      expect(apiMocks.createTicket).toHaveBeenCalledWith({
        title: 'Inventory sync issue',
        description: 'Stock sync failed for branch hq',
        category: 'general',
        priority: 'p2',
      })
    })

    await waitFor(() => {
      expect(apiMocks.listTickets).toHaveBeenCalledTimes(2)
    })
  })

  it('updates ticket status and reloads overview', async () => {
    render(<SupportPanel />)

    const moveInProgressButton = await screen.findByRole('button', {
      name: 'Set in progress SUP-20260406-0001',
    })

    await userEvent.click(moveInProgressButton)

    await waitFor(() => {
      expect(apiMocks.updateTicket).toHaveBeenCalledWith('ticket-1', {
        status: 'in_progress',
      })
    })

    await waitFor(() => {
      expect(apiMocks.getOverview).toHaveBeenCalledTimes(2)
    })
  })

  it('opens detail modal and loads ticket detail', async () => {
    render(<SupportPanel />)

    const detailButton = await screen.findByRole('button', {
      name: 'View detail SUP-20260406-0001',
    })
    await userEvent.click(detailButton)

    await waitFor(() => {
      expect(apiMocks.getTicket).toHaveBeenCalledWith('ticket-1')
    })

    expect(await screen.findByText('Ticket Detail: SUP-20260406-0001')).toBeInTheDocument()
    expect(screen.getByText('Initial triage complete')).toBeInTheDocument()
  })

  it('assigns ticket from detail modal and refreshes data', async () => {
    render(<SupportPanel />)

    const detailButton = await screen.findByRole('button', {
      name: 'View detail SUP-20260406-0001',
    })
    await userEvent.click(detailButton)

    await screen.findByText('Ticket Detail: SUP-20260406-0001')
    const assignInput = screen.getByLabelText('Assign To (User ID)')
    await userEvent.clear(assignInput)
    await userEvent.type(assignInput, 'user-999')
    await userEvent.click(screen.getByRole('button', { name: 'Assign' }))

    await waitFor(() => {
      expect(apiMocks.assignTicket).toHaveBeenCalledWith('ticket-1', {
        assignee_user_id: 'user-999',
      })
    })

    await waitFor(() => {
      expect(apiMocks.listTickets).toHaveBeenCalledTimes(2)
      expect(apiMocks.getOverview).toHaveBeenCalledTimes(2)
    })
  })

  it('adds comment from detail modal and reloads comments', async () => {
    render(<SupportPanel />)

    const detailButton = await screen.findByRole('button', {
      name: 'View detail SUP-20260406-0001',
    })
    await userEvent.click(detailButton)

    await screen.findByText('Ticket Detail: SUP-20260406-0001')
    await userEvent.type(screen.getByPlaceholderText('Add a comment...'), 'Need branch-level logs')
    await userEvent.click(screen.getByRole('button', { name: 'Add Comment' }))

    await waitFor(() => {
      expect(apiMocks.addComment).toHaveBeenCalledWith('ticket-1', {
        content: 'Need branch-level logs',
        is_internal: true,
      })
    })

    await waitFor(() => {
      expect(apiMocks.getTicket).toHaveBeenCalledTimes(2)
      expect(apiMocks.listTickets).toHaveBeenCalledTimes(2)
      expect(apiMocks.getOverview).toHaveBeenCalledTimes(2)
    })
  })

  it('updates status to resolved from detail modal', async () => {
    render(<SupportPanel />)

    const detailButton = await screen.findByRole('button', {
      name: 'View detail SUP-20260406-0001',
    })
    await userEvent.click(detailButton)

    await screen.findByText('Ticket Detail: SUP-20260406-0001')
    await userEvent.click(screen.getByRole('button', { name: 'Resolved' }))

    await waitFor(() => {
      expect(apiMocks.updateTicket).toHaveBeenCalledWith('ticket-1', {
        status: 'resolved',
      })
    })
  })

  it('shows permission error when assign fails with 403', async () => {
    apiMocks.assignTicket.mockRejectedValueOnce({
      status: 403,
      message: 'forbidden',
    })

    render(<SupportPanel />)

    const detailButton = await screen.findByRole('button', {
      name: 'View detail SUP-20260406-0001',
    })
    await userEvent.click(detailButton)

    await screen.findByText('Ticket Detail: SUP-20260406-0001')
    const assignInput = screen.getByLabelText('Assign To (User ID)')
    await userEvent.clear(assignInput)
    await userEvent.type(assignInput, 'user-111')
    await userEvent.click(screen.getByRole('button', { name: 'Assign' }))

    expect(await screen.findByText('Akses support ticketing hanya tersedia untuk admin/owner enterprise.')).toBeInTheDocument()
  })
})
