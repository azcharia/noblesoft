'use client'

import { useCallback, useEffect, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import { PageAlert } from '@/components/dashboard/PageAlert'
import { StatCard } from '@/components/dashboard/StatCard'
import {
  apiClient,
  type SupportOverviewResponse,
  type SupportPriority,
  type SupportTicket,
  type SupportTicketListResponse,
  type SupportTicketDetailResponse,
  type SupportTicketStatus,
} from '@/lib/api/client'

const emptyTicketList: SupportTicketListResponse = {
  tickets: [],
  total: 0,
  page: 1,
  page_size: 20,
  has_more: false,
}

const emptyOverview: SupportOverviewResponse = {
  total_open: 0,
  total_in_progress: 0,
  total_resolved: 0,
  total_closed: 0,
  sla_response_breached: 0,
  sla_resolution_breached: 0,
}

function toFriendlyError(error: unknown): string {
  if (error && typeof error === 'object') {
    const message = String((error as { message?: unknown }).message ?? '').trim()
    const status = Number((error as { status?: unknown }).status ?? 0)

    if (status === 403) {
      return 'Akses support ticketing hanya tersedia untuk admin/owner enterprise.'
    }

    if (status === 404) {
      return 'Ticket tidak ditemukan atau sudah berubah.'
    }

    if (message) {
      return message
    }
  }

  return 'Terjadi kesalahan saat memproses support ticket.'
}

export function SupportPanel() {
  const [ticketList, setTicketList] = useState<SupportTicketListResponse>(emptyTicketList)
  const [overview, setOverview] = useState<SupportOverviewResponse>(emptyOverview)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [processingTicketId, setProcessingTicketId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const [ticketTitle, setTicketTitle] = useState('')
  const [ticketDescription, setTicketDescription] = useState('')
  const [ticketPriority, setTicketPriority] = useState<SupportPriority>('p3')

  // Detail modal state
  const [selectedTicket, setSelectedTicket] = useState<SupportTicketDetailResponse | null>(null)
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [commentContent, setCommentContent] = useState('')
  const [isSubmittingComment, setIsSubmittingComment] = useState(false)
  const [assigneeUserId, setAssigneeUserId] = useState('')
  const [isAssigning, setIsAssigning] = useState(false)

  const loadSupportData = useCallback(async () => {
    try {
      setError(null)
      const [tickets, supportOverview] = await Promise.all([
        apiClient.operations.support.listTickets({ page: 1, page_size: 20 }),
        apiClient.operations.support.getOverview(),
      ])

      setTicketList(tickets)
      setOverview(supportOverview)
    } catch (err) {
      setError(toFriendlyError(err))
    }
  }, [])

  useEffect(() => {
    const run = async () => {
      setIsLoading(true)
      await loadSupportData()
      setIsLoading(false)
    }

    run()
  }, [loadSupportData])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await loadSupportData()
    setIsRefreshing(false)
  }

  const handleCreateTicket = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const normalizedTitle = ticketTitle.trim()
    const normalizedDescription = ticketDescription.trim()

    if (!normalizedTitle || !normalizedDescription) {
      setError('Judul dan deskripsi ticket wajib diisi.')
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)
      setSuccessMessage(null)

      await apiClient.operations.support.createTicket({
        title: normalizedTitle,
        description: normalizedDescription,
        category: 'general',
        priority: ticketPriority,
      })

      setTicketTitle('')
      setTicketDescription('')
      setTicketPriority('p3')
      setSuccessMessage('Ticket baru berhasil dibuat.')

      await loadSupportData()
    } catch (err) {
      setError(toFriendlyError(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleMoveToInProgress = async (ticket: SupportTicket) => {
    try {
      setProcessingTicketId(ticket.id)
      setError(null)
      setSuccessMessage(null)

      await apiClient.operations.support.updateTicket(ticket.id, {
        status: 'in_progress',
      })

      setSuccessMessage(`Ticket ${ticket.ticket_number} dipindahkan ke in progress.`)
      await loadSupportData()
    } catch (err) {
      setError(toFriendlyError(err))
    } finally {
      setProcessingTicketId(null)
    }
  }

  const handleViewDetail = async (ticket: SupportTicket) => {
    try {
      setIsLoadingDetail(true)
      setIsDetailModalOpen(true)
      setError(null)
      
      const detail = await apiClient.operations.support.getTicket(ticket.id)
      setSelectedTicket(detail)
      setAssigneeUserId(detail.ticket.assignee_user_id || '')
    } catch (err) {
      setError(toFriendlyError(err))
      setIsDetailModalOpen(false)
    } finally {
      setIsLoadingDetail(false)
    }
  }

  const handleCloseDetail = () => {
    setIsDetailModalOpen(false)
    setSelectedTicket(null)
    setCommentContent('')
    setAssigneeUserId('')
  }

  const handleAddComment = async () => {
    if (!selectedTicket || !commentContent.trim()) return

    try {
      setIsSubmittingComment(true)
      setError(null)
      
      await apiClient.operations.support.addComment(selectedTicket.ticket.id, {
        content: commentContent.trim(),
        is_internal: true,
      })

      setCommentContent('')
      setSuccessMessage('Komentar berhasil ditambahkan.')
      
      // Reload detail
      const detail = await apiClient.operations.support.getTicket(selectedTicket.ticket.id)
      setSelectedTicket(detail)
      await loadSupportData()
    } catch (err) {
      setError(toFriendlyError(err))
    } finally {
      setIsSubmittingComment(false)
    }
  }

  const handleAssignTicket = async () => {
    if (!selectedTicket || !assigneeUserId.trim()) {
      setError('User ID wajib diisi untuk assignment.')
      return
    }

    try {
      setIsAssigning(true)
      setError(null)
      
      await apiClient.operations.support.assignTicket(selectedTicket.ticket.id, {
        assignee_user_id: assigneeUserId.trim(),
      })

      setSuccessMessage('Ticket berhasil di-assign.')
      
      // Reload detail
      const detail = await apiClient.operations.support.getTicket(selectedTicket.ticket.id)
      setSelectedTicket(detail)
      await loadSupportData()
    } catch (err) {
      setError(toFriendlyError(err))
    } finally {
      setIsAssigning(false)
    }
  }

  const handleUpdateStatus = async (newStatus: SupportTicketStatus) => {
    if (!selectedTicket) return

    try {
      setError(null)
      
      await apiClient.operations.support.updateTicket(selectedTicket.ticket.id, {
        status: newStatus,
      })

      setSuccessMessage(`Status berhasil diubah ke ${newStatus}.`)
      
      // Reload detail
      const detail = await apiClient.operations.support.getTicket(selectedTicket.ticket.id)
      setSelectedTicket(detail)
      await loadSupportData()
    } catch (err) {
      setError(toFriendlyError(err))
    }
  }

  if (isLoading) {
    return <LoadingSpinner message="Memuat support ticketing..." />
  }

  return (
    <div className="space-y-6">
      {error ? <PageAlert variant="error" message={error} /> : null}
      {successMessage ? <PageAlert variant="success" message={successMessage} /> : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <StatCard title="Open Tickets" value={overview.total_open} tone="warning" />
        <StatCard title="In Progress" value={overview.total_in_progress} tone="accent" />
        <StatCard title="Resolved" value={overview.total_resolved} tone="success" />
        <StatCard title="SLA Breach" value={overview.sla_resolution_breached} tone="danger" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Buat Support Ticket</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleCreateTicket}>
            <div className="space-y-1.5">
              <Label htmlFor="support-ticket-title">Judul Ticket</Label>
              <Input
                id="support-ticket-title"
                name="support-ticket-title"
                value={ticketTitle}
                onChange={(event) => setTicketTitle(event.target.value)}
                placeholder="Contoh: Inventory sync issue"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="support-ticket-description">Deskripsi Ticket</Label>
              <Textarea
                id="support-ticket-description"
                name="support-ticket-description"
                value={ticketDescription}
                onChange={(event) => setTicketDescription(event.target.value)}
                placeholder="Jelaskan issue dan dampaknya"
                rows={3}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="support-ticket-priority">Priority</Label>
                <select
                  id="support-ticket-priority"
                  name="support-ticket-priority"
                  className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={ticketPriority}
                  onChange={(event) => setTicketPriority(event.target.value as SupportPriority)}
                >
                  <option value="p1">P1 - Critical</option>
                  <option value="p2">P2 - High</option>
                  <option value="p3">P3 - Normal</option>
                </select>
              </div>

              <div className="md:col-span-2 flex items-end justify-end">
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? 'Menyimpan...' : 'Buat Ticket'}
                </Button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle className="text-lg">Support Ticketing</CardTitle>
          <Button variant="outline" className="gap-2" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {ticketList.tickets.length === 0 ? (
            <p className="text-sm text-muted-foreground">Belum ada support ticket.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ticket</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>SLA</TableHead>
                  <TableHead className="text-right">Aksi</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {ticketList.tickets.map((ticket) => (
                  <TableRow key={ticket.id}>
                    <TableCell>
                      <p className="font-medium text-foreground">{ticket.title}</p>
                      <p className="text-xs text-muted-foreground">{ticket.ticket_number}</p>
                    </TableCell>
                    <TableCell>
                      <Badge variant={ticket.priority === 'p1' ? 'destructive' : 'secondary'}>
                        {ticket.priority.toUpperCase()}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={ticket.status === 'resolved' || ticket.status === 'closed' ? 'default' : 'secondary'}>
                        {ticket.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1 text-xs text-muted-foreground">
                        <p>Response: {ticket.is_sla_response_breached ? 'Breached' : 'On Track'}</p>
                        <p>Resolution: {ticket.is_sla_resolution_breached ? 'Breached' : 'On Track'}</p>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          aria-label={`View detail ${ticket.ticket_number}`}
                          onClick={() => handleViewDetail(ticket)}
                        >
                          Detail
                        </Button>
                        {ticket.status === 'open' ? (
                          <Button
                            size="sm"
                            variant="outline"
                            aria-label={`Set in progress ${ticket.ticket_number}`}
                            disabled={processingTicketId === ticket.id}
                            onClick={() => handleMoveToInProgress(ticket)}
                          >
                            {processingTicketId === ticket.id ? 'Memproses...' : 'Set In Progress'}
                          </Button>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Ticket Detail Modal */}
      <Dialog open={isDetailModalOpen} onOpenChange={(open) => {
        if (!open) handleCloseDetail()
      }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {selectedTicket ? `Ticket Detail: ${selectedTicket.ticket.ticket_number}` : 'Loading...'}
            </DialogTitle>
          </DialogHeader>
          
          {isLoadingDetail ? (
            <p className="text-sm text-muted-foreground">Memuat detail ticket...</p>
          ) : selectedTicket ? (
            <div className="space-y-6">
              {/* Ticket Info */}
              <div className="space-y-3">
                <div>
                  <Label className="text-xs font-medium text-muted-foreground">Title</Label>
                  <p className="text-sm font-medium">{selectedTicket.ticket.title}</p>
                </div>
                
                {selectedTicket.ticket.description && (
                  <div>
                    <Label className="text-xs font-medium text-muted-foreground">Description</Label>
                    <p className="text-sm">{selectedTicket.ticket.description}</p>
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs font-medium text-muted-foreground">Priority</Label>
                    <div className="mt-1">
                      <Badge variant={selectedTicket.ticket.priority === 'p1' ? 'destructive' : 'secondary'}>
                        {selectedTicket.ticket.priority.toUpperCase()}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs font-medium text-muted-foreground">Status</Label>
                    <div className="mt-1">
                      <Badge variant={selectedTicket.ticket.status === 'resolved' || selectedTicket.ticket.status === 'closed' ? 'default' : 'secondary'}>
                        {selectedTicket.ticket.status}
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>

              {/* Status Actions */}
              <div className="space-y-2">
                <Label className="text-xs font-medium">Change Status</Label>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" onClick={() => handleUpdateStatus('open')} disabled={selectedTicket.ticket.status === 'open'}>
                    Open
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleUpdateStatus('in_progress')} disabled={selectedTicket.ticket.status === 'in_progress'}>
                    In Progress
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleUpdateStatus('resolved')} disabled={selectedTicket.ticket.status === 'resolved'}>
                    Resolved
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleUpdateStatus('closed')} disabled={selectedTicket.ticket.status === 'closed'}>
                    Closed
                  </Button>
                </div>
              </div>

              {/* Assignment */}
              <div className="space-y-2">
                <Label htmlFor="assign-user" className="text-xs font-medium">Assign To (User ID)</Label>
                <div className="flex gap-2">
                  <Input
                    id="assign-user"
                    name="assign-user"
                    value={assigneeUserId}
                    onChange={(e) => setAssigneeUserId(e.target.value)}
                    placeholder="Enter user ID"
                    className="flex-1"
                  />
                  <Button onClick={handleAssignTicket} disabled={isAssigning || !assigneeUserId.trim()}>
                    {isAssigning ? 'Assigning...' : 'Assign'}
                  </Button>
                </div>
                {selectedTicket.ticket.assignee_user_id && (
                  <p className="text-xs text-muted-foreground">
                    Current assignee: {selectedTicket.ticket.assignee_user_id}
                  </p>
                )}
              </div>

              {/* Comments */}
              <div className="space-y-3">
                <Label className="text-xs font-medium">Comments ({selectedTicket.comments.length})</Label>
                
                {selectedTicket.comments.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Belum ada komentar.</p>
                ) : (
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {selectedTicket.comments.map((comment) => (
                      <div key={comment.id} className="rounded-lg border bg-muted/50 p-3">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm">{comment.content}</p>
                          <Badge variant={comment.is_internal ? 'secondary' : 'default'} className="shrink-0">
                            {comment.is_internal ? 'Internal' : 'Public'}
                          </Badge>
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {new Date(comment.created_at).toLocaleString('id-ID')}
                          {comment.author_user_id && ` • ${comment.author_user_id}`}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                <div className="space-y-2">
                  <Textarea
                    name="ticket-comment"
                    value={commentContent}
                    onChange={(e) => setCommentContent(e.target.value)}
                    placeholder="Add a comment..."
                    rows={3}
                  />
                  <Button onClick={handleAddComment} disabled={isSubmittingComment || !commentContent.trim()}>
                    {isSubmittingComment ? 'Menambahkan...' : 'Add Comment'}
                  </Button>
                </div>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
