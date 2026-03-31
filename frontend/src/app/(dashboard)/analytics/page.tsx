/**
 * Analytics Page
 * Lightweight KPI visualization from live API data.
 */
'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { BarChart3, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageAlert } from '@/components/dashboard/PageAlert'
import { PageHeader } from '@/components/dashboard/PageHeader'
import { StatCard } from '@/components/dashboard/StatCard'
import { apiClient, type Invoice, type Product } from '@/lib/api/client'
import { formatCurrency } from '@/lib/utils'

export default function AnalyticsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const [productsData, invoicesData] = await Promise.all([
        apiClient.products.list({ page: 1, page_size: 100, is_active: true }),
        apiClient.invoices.list({ page: 1, page_size: 100 }),
      ])

      setProducts(productsData.products)
      setInvoices(invoicesData.invoices)
    } catch (err) {
      console.error('Failed to load analytics data:', err)
      setError('Gagal memuat data analytics. Coba refresh kembali.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const paymentDistribution = useMemo(() => {
    const base = {
      unpaid: 0,
      partial: 0,
      paid: 0,
      overdue: 0,
    }

    for (const invoice of invoices) {
      base[invoice.payment_status] += 1
    }

    return base
  }, [invoices])

  const categoryDistribution = useMemo(() => {
    const bucket = new Map<string, number>()

    for (const product of products) {
      const category = product.category || 'Uncategorized'
      bucket.set(category, (bucket.get(category) || 0) + 1)
    }

    return [...bucket.entries()].sort((a, b) => b[1] - a[1])
  }, [products])

  const overdueAmount = invoices
    .filter((invoice) => invoice.payment_status === 'overdue')
    .reduce((sum, invoice) => sum + Number(invoice.total_amount || 0), 0)

  return (
    <div className="space-y-6">
      <PageHeader
        label="Insights"
        title="Analytics"
        description="Ringkasan metrik bisnis berbasis data invoice dan produk."
        actions={
          <Button
            variant="outline"
            className="w-full gap-2 sm:w-auto"
            onClick={loadData}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        }
      />

      {error ? <PageAlert message={error} variant="error" /> : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard title="Total Produk" value={products.length} />
        <StatCard title="Total Invoice" value={invoices.length} />
        <StatCard title="Nilai Overdue" value={formatCurrency(overdueAmount)} tone="danger" />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Distribusi Status Invoice
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(paymentDistribution).map(([status, count]) => (
              <div key={status} className="space-y-1">
                <div className="flex items-center justify-between text-sm">
                  <span className="capitalize text-muted-foreground">{status}</span>
                  <span className="font-semibold text-foreground">{count}</span>
                </div>
                <div className="h-2 w-full rounded-full bg-muted">
                  <div
                    className="h-2 rounded-full bg-gradient-accent-horizontal"
                    style={{ width: `${invoices.length ? (count / invoices.length) * 100 : 0}%` }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Distribusi Kategori Produk</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {categoryDistribution.length === 0 ? (
              <p className="text-sm text-muted-foreground">Belum ada data kategori produk.</p>
            ) : (
              categoryDistribution.map(([category, count]) => (
                <div key={category} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{category}</span>
                    <span className="font-semibold text-foreground">{count}</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted">
                    <div
                      className="h-2 rounded-full bg-emerald-500"
                      style={{ width: `${products.length ? (count / products.length) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
