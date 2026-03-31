/**
 * Invoices Page
 * Invoice listing with status update actions.
 */
'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { FileText, Filter, RefreshCw, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { PageAlert } from '@/components/dashboard/PageAlert'
import { PageHeader } from '@/components/dashboard/PageHeader'
import { StatCard } from '@/components/dashboard/StatCard'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { apiClient, type Invoice } from '@/lib/api/client'
import { formatCurrency, formatDate } from '@/lib/utils'

type InvoiceStatusFilter = 'all' | 'unpaid' | 'partial' | 'paid' | 'overdue'

const STATUS_FILTERS: InvoiceStatusFilter[] = [
  'all',
  'unpaid',
  'partial',
  'paid',
  'overdue',
]

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isUpdatingId, setIsUpdatingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<InvoiceStatusFilter>('all')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  const loadInvoices = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const data = await apiClient.invoices.list({
        page,
        page_size: 20,
        customer_name: search || undefined,
        payment_status: statusFilter === 'all' ? undefined : statusFilter,
      })

      setInvoices(data.invoices)
      setTotal(data.total)
      setHasMore(data.has_more)
    } catch (err) {
      console.error('Failed to load invoices:', err)
      setError('Gagal memuat daftar invoice. Coba refresh kembali.')
    } finally {
      setIsLoading(false)
    }
  }, [page, search, statusFilter])

  useEffect(() => {
    loadInvoices()
  }, [loadInvoices])

  const summary = useMemo(() => {
    const paid = invoices
      .filter((invoice) => invoice.payment_status === 'paid')
      .reduce((sum, invoice) => sum + Number(invoice.total_amount || 0), 0)

    const unpaidCount = invoices.filter(
      (invoice) => invoice.payment_status === 'unpaid' || invoice.payment_status === 'overdue'
    ).length

    return {
      paid,
      unpaidCount,
    }
  }, [invoices])

  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1)
  }

  const handleFilterChange = (value: InvoiceStatusFilter) => {
    setStatusFilter(value)
    setPage(1)
  }

  const updateStatus = async (invoice: Invoice, nextStatus: 'paid' | 'unpaid') => {
    try {
      setIsUpdatingId(invoice.id)
      await apiClient.invoices.updatePaymentStatus(invoice.id, nextStatus)
      await loadInvoices()
    } catch (err) {
      console.error('Failed to update payment status:', err)
      setError('Gagal memperbarui status pembayaran invoice.')
    } finally {
      setIsUpdatingId(null)
    }
  }

  const getStatusBadge = (status: Invoice['payment_status']) => {
    if (status === 'paid') {
      return <Badge variant="default">Paid</Badge>
    }

    if (status === 'partial') {
      return <Badge variant="outline">Partial</Badge>
    }

    if (status === 'overdue') {
      return <Badge variant="destructive">Overdue</Badge>
    }

    return <Badge variant="secondary">Unpaid</Badge>
  }

  return (
    <div className="space-y-6">
      <PageHeader
        label="Billing"
        title="Invoices"
        description="Monitor invoice status dan pembayaran customer."
        actions={
          <Button
            variant="outline"
            className="w-full gap-2 sm:w-auto"
            onClick={loadInvoices}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        }
      />

      {error ? <PageAlert message={error} variant="error" /> : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard
          title="Total Invoice"
          subtitle="halaman aktif"
          value={invoices.length}
          tone="default"
        />
        <StatCard
          title="Belum Lunas"
          subtitle="halaman aktif"
          value={summary.unpaidCount}
          tone="danger"
        />
        <StatCard
          title="Revenue Lunas"
          subtitle="halaman aktif"
          value={formatCurrency(summary.paid)}
          tone="success"
        />
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="min-w-[260px] flex-1 max-w-lg relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Cari customer name..."
            value={search}
            onChange={(event) => handleSearch(event.target.value)}
            className="pl-10"
          />
        </div>

        <div className="flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 shadow-sm">
          <Filter className="h-4 w-4 text-muted-foreground" />
          {STATUS_FILTERS.map((filter) => (
            <Button
              key={filter}
              variant={statusFilter === filter ? 'default' : 'ghost'}
              size="sm"
              onClick={() => handleFilterChange(filter)}
              className="capitalize"
            >
              {filter}
            </Button>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Invoice</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Issue / Due</TableHead>
              <TableHead className="text-right">Total</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>

          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                  Loading invoices...
                </TableCell>
              </TableRow>
            ) : invoices.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                  <div className="mx-auto flex max-w-sm flex-col items-center gap-2">
                    <FileText className="h-6 w-6 text-muted-foreground" />
                    <p>Tidak ada invoice ditemukan untuk filter saat ini.</p>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              invoices.map((invoice) => {
                const isUpdating = isUpdatingId === invoice.id
                const canMarkPaid = invoice.payment_status !== 'paid'

                return (
                  <TableRow key={invoice.id}>
                    <TableCell>
                      <p className="font-medium text-foreground">{invoice.invoice_number}</p>
                      <p className="text-xs text-muted-foreground">{invoice.items.length} item</p>
                    </TableCell>
                    <TableCell>
                      <p className="font-medium text-foreground">{invoice.customer_name}</p>
                      <p className="text-xs text-muted-foreground">{invoice.customer_email || '-'}</p>
                    </TableCell>
                    <TableCell>
                      <p className="text-sm text-foreground">Issue: {formatDate(invoice.issue_date)}</p>
                      <p className="text-xs text-muted-foreground">
                        Due: {invoice.due_date ? formatDate(invoice.due_date) : '-'}
                      </p>
                    </TableCell>
                    <TableCell className="text-right font-semibold">
                      {formatCurrency(invoice.total_amount)}
                    </TableCell>
                    <TableCell>{getStatusBadge(invoice.payment_status)}</TableCell>
                    <TableCell className="text-right">
                      <div className="inline-flex gap-2">
                        <Button
                          size="sm"
                          variant={canMarkPaid ? 'default' : 'outline'}
                          disabled={isUpdating || !canMarkPaid}
                          onClick={() => updateStatus(invoice, 'paid')}
                        >
                          Mark Paid
                        </Button>
                        <Button
                          size="sm"
                          variant={!canMarkPaid ? 'default' : 'outline'}
                          disabled={isUpdating || canMarkPaid}
                          onClick={() => updateStatus(invoice, 'unpaid')}
                        >
                          Reopen
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>

        {!isLoading && invoices.length > 0 && (
          <div className="flex items-center justify-between border-t border-border px-6 py-4">
            <p className="text-sm text-muted-foreground">
              Showing {(page - 1) * 20 + 1} to {Math.min(page * 20, total)} of {total} invoices
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page === 1}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((current) => current + 1)}
                disabled={!hasMore}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
