'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/ui/loading-spinner'
import { Textarea } from '@/components/ui/textarea'
import { PageAlert } from '@/components/dashboard/PageAlert'
import { StatCard } from '@/components/dashboard/StatCard'
import {
  apiClient,
  type QBRDashboardResponse,
  type QBRGoal,
} from '@/lib/api/client'
import { formatCurrency } from '@/lib/utils'

const emptyDashboard: QBRDashboardResponse = {
  cycle: null,
  goals: [],
  metrics: {
    paid_revenue: 0,
    unpaid_invoice_count: 0,
    total_products: 0,
    low_stock_products: 0,
  },
}

function toFriendlyError(error: unknown): string {
  if (error && typeof error === 'object') {
    const message = String((error as { message?: unknown }).message ?? '').trim()
    const status = Number((error as { status?: unknown }).status ?? 0)

    if (status === 403) {
      return 'Akses QBR hanya tersedia untuk admin/owner tenant enterprise.'
    }

    if (status === 404) {
      return 'Cycle atau goal QBR tidak ditemukan.'
    }

    if (message) {
      return message
    }
  }

  return 'Terjadi kesalahan saat memproses QBR dashboard.'
}

export function QBRPanel() {
  const [dashboard, setDashboard] = useState<QBRDashboardResponse>(emptyDashboard)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isSubmittingCycle, setIsSubmittingCycle] = useState(false)
  const [processingGoalId, setProcessingGoalId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const [quarterCode, setQuarterCode] = useState('')
  const [cycleTitle, setCycleTitle] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  // Goal creation form state
  const [goalTitle, setGoalTitle] = useState('')
  const [goalDescription, setGoalDescription] = useState('')
  const [goalMetricName, setGoalMetricName] = useState('')
  const [goalUnit, setGoalUnit] = useState('')
  const [goalTargetValue, setGoalTargetValue] = useState('')
  const [goalCurrentValue, setGoalCurrentValue] = useState('0')
  const [goalStatus, setGoalStatus] = useState<'on_track' | 'at_risk' | 'off_track' | 'achieved'>('on_track')
  const [goalDueDate, setGoalDueDate] = useState('')
  const [goalOwnerUserId, setGoalOwnerUserId] = useState('')
  const [isSubmittingGoal, setIsSubmittingGoal] = useState(false)

  const loadDashboard = useCallback(async () => {
    try {
      setError(null)
      const data = await apiClient.operations.qbr.getDashboard()
      setDashboard(data)
    } catch (err) {
      setError(toFriendlyError(err))
    }
  }, [])

  useEffect(() => {
    const run = async () => {
      setIsLoading(true)
      await loadDashboard()
      setIsLoading(false)
    }

    run()
  }, [loadDashboard])

  const activeCycleLabel = useMemo(() => {
    if (!dashboard.cycle) {
      return 'Belum ada cycle aktif'
    }
    return `${dashboard.cycle.quarter_code} - ${dashboard.cycle.title || 'Quarterly Review'}`
  }, [dashboard.cycle])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await loadDashboard()
    setIsRefreshing(false)
  }

  const handleCreateCycle = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const normalizedQuarter = quarterCode.trim().toUpperCase()
    const normalizedTitle = cycleTitle.trim()

    if (!normalizedQuarter || !normalizedTitle || !startDate || !endDate) {
      setError('Quarter, cycle title, start date, dan end date wajib diisi.')
      return
    }

    try {
      setIsSubmittingCycle(true)
      setError(null)
      setSuccessMessage(null)

      await apiClient.operations.qbr.createCycle({
        quarter_code: normalizedQuarter,
        title: normalizedTitle,
        start_date: startDate,
        end_date: endDate,
        status: 'draft',
      })

      setQuarterCode('')
      setCycleTitle('')
      setStartDate('')
      setEndDate('')
      setSuccessMessage('Cycle QBR berhasil dibuat.')

      await loadDashboard()
    } catch (err) {
      setError(toFriendlyError(err))
    } finally {
      setIsSubmittingCycle(false)
    }
  }

  const handleUpdateGoalProgress = async (goal: QBRGoal) => {
    try {
      setProcessingGoalId(goal.id)
      setError(null)
      setSuccessMessage(null)

      const nextValue = goal.current_value < 100000000 ? 100000000 : goal.current_value
      await apiClient.operations.qbr.updateGoal(goal.id, {
        current_value: nextValue,
      })

      setSuccessMessage(`Progress goal ${goal.title} berhasil diperbarui.`)
      await loadDashboard()
    } catch (err) {
      setError(toFriendlyError(err))
    } finally {
      setProcessingGoalId(null)
    }
  }

  const handleCreateGoal = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!dashboard.cycle) {
      setError('Cycle aktif diperlukan untuk membuat goal.')
      return
    }

    const normalizedTitle = goalTitle.trim()
    const normalizedTargetValue = parseFloat(goalTargetValue)
    const normalizedCurrentValue = parseFloat(goalCurrentValue)

    if (!normalizedTitle || isNaN(normalizedTargetValue)) {
      setError('Title dan target value wajib diisi dengan benar.')
      return
    }

    try {
      setIsSubmittingGoal(true)
      setError(null)
      setSuccessMessage(null)

      await apiClient.operations.qbr.createGoal({
        cycle_id: dashboard.cycle.id,
        title: normalizedTitle,
        description: goalDescription.trim() || undefined,
        metric_name: goalMetricName.trim() || undefined,
        unit: goalUnit.trim() || undefined,
        target_value: normalizedTargetValue,
        current_value: isNaN(normalizedCurrentValue) ? 0 : normalizedCurrentValue,
        status: goalStatus,
        due_date: goalDueDate || undefined,
        owner_user_id: goalOwnerUserId.trim() || undefined,
      })

      // Reset form
      setGoalTitle('')
      setGoalDescription('')
      setGoalMetricName('')
      setGoalUnit('')
      setGoalTargetValue('')
      setGoalCurrentValue('0')
      setGoalStatus('on_track')
      setGoalDueDate('')
      setGoalOwnerUserId('')
      
      setSuccessMessage('Goal QBR berhasil dibuat.')
      await loadDashboard()
    } catch (err) {
      setError(toFriendlyError(err))
    } finally {
      setIsSubmittingGoal(false)
    }
  }

  if (isLoading) {
    return <LoadingSpinner message="Memuat QBR dashboard..." />
  }

  return (
    <div className="space-y-6">
      {error ? <PageAlert variant="error" message={error} /> : null}
      {successMessage ? <PageAlert variant="success" message={successMessage} /> : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <StatCard title="Paid Revenue" value={formatCurrency(dashboard.metrics.paid_revenue)} tone="success" />
        <StatCard title="Unpaid Invoices" value={dashboard.metrics.unpaid_invoice_count} tone="warning" />
        <StatCard title="Total Products" value={dashboard.metrics.total_products} />
        <StatCard title="Low Stock Products" value={dashboard.metrics.low_stock_products} tone="danger" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Buat QBR Cycle</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleCreateCycle}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="qbr-quarter">Quarter</Label>
                <Input
                  id="qbr-quarter"
                  name="qbr-quarter"
                  value={quarterCode}
                  onChange={(event) => setQuarterCode(event.target.value)}
                  placeholder="2026-Q3"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="qbr-cycle-title">Cycle Title</Label>
                <Input
                  id="qbr-cycle-title"
                  name="qbr-cycle-title"
                  value={cycleTitle}
                  onChange={(event) => setCycleTitle(event.target.value)}
                  placeholder="Q3 2026 Review"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="qbr-start-date">Start Date</Label>
                <Input
                  id="qbr-start-date"
                  name="qbr-start-date"
                  type="date"
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="qbr-end-date">End Date</Label>
                <Input
                  id="qbr-end-date"
                  name="qbr-end-date"
                  type="date"
                  value={endDate}
                  onChange={(event) => setEndDate(event.target.value)}
                />
              </div>
              <div className="flex items-end justify-end">
                <Button type="submit" disabled={isSubmittingCycle}>
                  {isSubmittingCycle ? 'Menyimpan...' : 'Buat Cycle'}
                </Button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      {dashboard.cycle && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Buat QBR Goal</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleCreateGoal}>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="goal-title">Title<span className="text-destructive">*</span></Label>
                  <Input
                    id="goal-title"
                    name="goal-title"
                    value={goalTitle}
                    onChange={(e) => setGoalTitle(e.target.value)}
                    placeholder="e.g., Increase Monthly Revenue"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="goal-metric-name">Metric Name</Label>
                  <Input
                    id="goal-metric-name"
                    name="goal-metric-name"
                    value={goalMetricName}
                    onChange={(e) => setGoalMetricName(e.target.value)}
                    placeholder="e.g., monthly_revenue"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="goal-description">Description</Label>
                <Textarea
                  id="goal-description"
                  name="goal-description"
                  value={goalDescription}
                  onChange={(e) => setGoalDescription(e.target.value)}
                  placeholder="Optional goal description"
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div className="space-y-1.5">
                  <Label htmlFor="goal-target-value">Target Value<span className="text-destructive">*</span></Label>
                  <Input
                    id="goal-target-value"
                    name="goal-target-value"
                    type="number"
                    value={goalTargetValue}
                    onChange={(e) => setGoalTargetValue(e.target.value)}
                    placeholder="e.g., 100000000"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="goal-current-value">Current Value</Label>
                  <Input
                    id="goal-current-value"
                    name="goal-current-value"
                    type="number"
                    value={goalCurrentValue}
                    onChange={(e) => setGoalCurrentValue(e.target.value)}
                    placeholder="e.g., 0"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="goal-unit">Unit</Label>
                  <Input
                    id="goal-unit"
                    name="goal-unit"
                    value={goalUnit}
                    onChange={(e) => setGoalUnit(e.target.value)}
                    placeholder="e.g., IDR, units"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div className="space-y-1.5">
                  <Label htmlFor="goal-status">Status</Label>
                  <select
                    id="goal-status"
                    name="goal-status"
                    className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                    value={goalStatus}
                    onChange={(e) => setGoalStatus(e.target.value as typeof goalStatus)}
                  >
                    <option value="on_track">On Track</option>
                    <option value="at_risk">At Risk</option>
                    <option value="off_track">Off Track</option>
                    <option value="achieved">Achieved</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="goal-due-date">Due Date</Label>
                  <Input
                    id="goal-due-date"
                    name="goal-due-date"
                    type="date"
                    value={goalDueDate}
                    onChange={(e) => setGoalDueDate(e.target.value)}
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="goal-owner">Owner User ID</Label>
                  <Input
                    id="goal-owner"
                    name="goal-owner"
                    value={goalOwnerUserId}
                    onChange={(e) => setGoalOwnerUserId(e.target.value)}
                    placeholder="Optional user ID"
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <Button type="submit" disabled={isSubmittingGoal}>
                  {isSubmittingGoal ? 'Menyimpan...' : 'Buat Goal'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div>
            <CardTitle className="text-lg">QBR Dashboard</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">{activeCycleLabel}</p>
          </div>
          <Button variant="outline" className="gap-2" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {dashboard.goals.length === 0 ? (
            <p className="text-sm text-muted-foreground">Belum ada goals untuk cycle aktif.</p>
          ) : (
            <div className="space-y-3">
              {dashboard.goals.map((goal) => (
                <div
                  key={goal.id}
                  className="rounded-xl border border-border/80 bg-background/70 p-4"
                >
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="font-semibold text-foreground">{goal.title}</p>
                      <p className="text-sm text-muted-foreground">{goal.metric_name || 'general_metric'}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Progress: {goal.current_value} / {goal.target_value} ({goal.progress_percentage}%)
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={goal.status === 'achieved' ? 'default' : 'secondary'}>
                        {goal.status}
                      </Badge>
                      <Button
                        size="sm"
                        variant="outline"
                        aria-label={`Update progress ${goal.id}`}
                        disabled={processingGoalId === goal.id}
                        onClick={() => handleUpdateGoalProgress(goal)}
                      >
                        {processingGoalId === goal.id ? 'Memproses...' : 'Update Progress'}
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
