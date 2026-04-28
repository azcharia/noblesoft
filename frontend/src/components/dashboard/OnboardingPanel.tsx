'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { CheckCircle2, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Textarea } from '@/components/ui/textarea'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { PageAlert } from '@/components/dashboard/PageAlert'
import { StatCard } from '@/components/dashboard/StatCard'
import {
  apiClient,
  type OnboardingChecklistResponse,
  type OnboardingItem,
} from '@/lib/api/client'

const emptyChecklist: OnboardingChecklistResponse = {
  items: [],
  total: 0,
  completed: 0,
  pending: 0,
  completion_rate: 0,
}

function toFriendlyError(error: unknown): string {
  if (error && typeof error === 'object') {
    const message = String((error as { message?: unknown }).message ?? '').trim()
    const status = Number((error as { status?: unknown }).status ?? 0)

    if (status === 403) {
      return 'Akses onboarding hanya tersedia untuk admin/owner tenant enterprise.'
    }

    if (status === 404) {
      return 'Task onboarding tidak ditemukan atau sudah berubah.'
    }

    if (status === 400 && /already exists/i.test(message)) {
      return 'Task dengan kode tersebut sudah ada.'
    }

    if (message) {
      return message
    }
  }

  return 'Terjadi kesalahan saat memproses onboarding checklist.'
}

export function OnboardingPanel() {
  const [checklist, setChecklist] = useState<OnboardingChecklistResponse>(emptyChecklist)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [processingItemId, setProcessingItemId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const [taskCode, setTaskCode] = useState('')
  const [taskTitle, setTaskTitle] = useState('')
  const [taskCategory, setTaskCategory] = useState('workspace')

  // Edit modal state
  const [editingItem, setEditingItem] = useState<OnboardingItem | null>(null)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [editCategory, setEditCategory] = useState('')
  const [editStatus, setEditStatus] = useState<'pending' | 'in_progress' | 'completed' | 'skipped'>('pending')
  const [editDueDate, setEditDueDate] = useState('')
  const [editIsRequired, setEditIsRequired] = useState(true)
  const [isUpdating, setIsUpdating] = useState(false)

  const loadChecklist = useCallback(async () => {
    try {
      setError(null)
      const data = await apiClient.operations.onboarding.list()
      setChecklist(data)
    } catch (err) {
      setError(toFriendlyError(err))
    }
  }, [])

  useEffect(() => {
    const run = async () => {
      setIsLoading(true)
      await loadChecklist()
      setIsLoading(false)
    }

    run()
  }, [loadChecklist])

  const completionPercent = useMemo(() => Math.round(checklist.completion_rate || 0), [checklist.completion_rate])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await loadChecklist()
    setIsRefreshing(false)
  }

  const handleCreateTask = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const normalizedCode = taskCode.trim().toLowerCase().replace(/\s+/g, '_')
    const normalizedTitle = taskTitle.trim()

    if (!normalizedCode || !normalizedTitle) {
      setError('Kode task dan judul task wajib diisi.')
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)
      setSuccessMessage(null)

      await apiClient.operations.onboarding.createItem({
        code: normalizedCode,
        title: normalizedTitle,
        category: taskCategory,
        is_required: true,
      })

      setTaskCode('')
      setTaskTitle('')
      setSuccessMessage('Task onboarding berhasil ditambahkan.')
      await loadChecklist()
    } catch (err) {
      setError(toFriendlyError(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCompleteTask = async (item: OnboardingItem) => {
    try {
      setProcessingItemId(item.id)
      setError(null)
      setSuccessMessage(null)

      await apiClient.operations.onboarding.completeItem(item.id)
      setSuccessMessage(`Task ${item.code} berhasil ditandai selesai.`)
      await loadChecklist()
    } catch (err) {
      setError(toFriendlyError(err))
    } finally {
      setProcessingItemId(null)
    }
  }

  const handleEditItem = (item: OnboardingItem) => {
    setEditingItem(item)
    setEditTitle(item.title)
    setEditDescription(item.description || '')
    setEditCategory(item.category)
    setEditStatus(item.status)
    setEditDueDate(item.due_date || '')
    setEditIsRequired(item.is_required)
    setIsEditModalOpen(true)
  }

  const handleCloseEdit = () => {
    setIsEditModalOpen(false)
    setEditingItem(null)
    setEditTitle('')
    setEditDescription('')
    setEditCategory('')
    setEditStatus('pending')
    setEditDueDate('')
    setEditIsRequired(true)
  }

  const handleUpdateItem = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!editingItem) return

    try {
      setIsUpdating(true)
      setError(null)

      await apiClient.operations.onboarding.updateItem(editingItem.id, {
        title: editTitle.trim() || undefined,
        description: editDescription.trim() || undefined,
        category: editCategory.trim() || undefined,
        status: editStatus,
        due_date: editDueDate || undefined,
        is_required: editIsRequired,
      })

      setSuccessMessage(`Task ${editingItem.code} berhasil diperbarui.`)
      handleCloseEdit()
      await loadChecklist()
    } catch (err) {
      setError(toFriendlyError(err))
    } finally {
      setIsUpdating(false)
    }
  }

  if (isLoading) {
    return <LoadingSpinner message="Memuat onboarding checklist..." />
  }

  return (
    <div className="space-y-6">
      {error ? <PageAlert variant="error" message={error} /> : null}
      {successMessage ? <PageAlert variant="success" message={successMessage} /> : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard title="Total Tasks" value={checklist.total} subtitle="aktivitas onboarding" />
        <StatCard title="Completed" value={checklist.completed} subtitle="task selesai" tone="success" />
        <StatCard title="Completion Rate" value={`${completionPercent}%`} subtitle="progress tenant" tone="accent" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Tambah Task Onboarding</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleCreateTask}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="onboarding-task-code">Kode Task</Label>
                <Input
                  id="onboarding-task-code"
                  name="onboarding-task-code"
                  value={taskCode}
                  onChange={(event) => setTaskCode(event.target.value)}
                  placeholder="invite_core_team"
                />
              </div>

              <div className="space-y-1.5 md:col-span-2">
                <Label htmlFor="onboarding-task-title">Judul Task</Label>
                <Input
                  id="onboarding-task-title"
                  name="onboarding-task-title"
                  value={taskTitle}
                  onChange={(event) => setTaskTitle(event.target.value)}
                  placeholder="Undang tim inti"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="onboarding-task-category">Kategori</Label>
                <Input
                  id="onboarding-task-category"
                  name="onboarding-task-category"
                  value={taskCategory}
                  onChange={(event) => setTaskCategory(event.target.value)}
                  placeholder="workspace"
                />
              </div>
              <div className="md:col-span-2 flex items-end justify-end">
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? 'Menyimpan...' : 'Tambah Task'}
                </Button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle className="text-lg">Onboarding Checklist</CardTitle>
          <Button variant="outline" className="gap-2" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {checklist.items.length === 0 ? (
            <p className="text-sm text-muted-foreground">Belum ada task onboarding untuk tenant ini.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead className="text-right">Aksi</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {checklist.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      <p className="font-medium text-foreground">{item.title}</p>
                      <p className="text-xs text-muted-foreground">{item.code}</p>
                    </TableCell>
                    <TableCell>
                      <Badge variant={item.status === 'completed' ? 'default' : 'secondary'}>
                        {item.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">{item.category}</span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button
                          size="sm"
                          variant="outline"
                          aria-label={`Edit ${item.code}`}
                          onClick={() => handleEditItem(item)}
                        >
                          Edit
                        </Button>
                        {item.status === 'completed' ? (
                          <span className="inline-flex items-center gap-1 text-xs text-emerald-600">
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Done
                          </span>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            aria-label={`Tandai selesai ${item.code}`}
                            disabled={processingItemId === item.id}
                            onClick={() => handleCompleteTask(item)}
                          >
                            {processingItemId === item.id ? 'Memproses...' : 'Tandai Selesai'}
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Edit Modal */}
      <Dialog open={isEditModalOpen} onOpenChange={(open) => {
        if (!open) handleCloseEdit()
      }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingItem ? `Edit Task: ${editingItem.code}` : 'Edit Task'}
            </DialogTitle>
          </DialogHeader>
          
          {editingItem && (
            <form onSubmit={handleUpdateItem} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="edit-title">Title</Label>
                <Input
                  id="edit-title"
                  name="edit-title"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  placeholder="Task title"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="edit-description">Description</Label>
                <Textarea
                  id="edit-description"
                  name="edit-description"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  placeholder="Optional description"
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="edit-category">Category</Label>
                  <Input
                    id="edit-category"
                    name="edit-category"
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value)}
                    placeholder="e.g., workspace"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="edit-status">Status</Label>
                  <select
                    id="edit-status"
                    name="edit-status"
                    className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    value={editStatus}
                    onChange={(e) => setEditStatus(e.target.value as typeof editStatus)}
                  >
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                    <option value="skipped">Skipped</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="edit-due-date">Due Date</Label>
                  <Input
                    id="edit-due-date"
                    name="edit-due-date"
                    type="date"
                    value={editDueDate}
                    onChange={(e) => setEditDueDate(e.target.value)}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={editIsRequired}
                      onChange={(e) => setEditIsRequired(e.target.checked)}
                      className="h-4 w-4"
                    />
                    <span>Is Required</span>
                  </Label>
                </div>
              </div>

              <div className="flex gap-2 justify-end">
                <Button type="button" variant="outline" onClick={handleCloseEdit}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isUpdating}>
                  {isUpdating ? 'Menyimpan...' : 'Update Task'}
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
