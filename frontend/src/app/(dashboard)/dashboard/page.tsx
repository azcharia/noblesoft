/**
 * Dashboard Page
 * High-level business snapshot for daily operations.
 */
'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { BarChart3, FileText, MessageSquare, Package, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PageAlert } from '@/components/dashboard/PageAlert'
import { PageHeader } from '@/components/dashboard/PageHeader'
import { StatCard } from '@/components/dashboard/StatCard'
import { apiClient, type Invoice, type Product } from '@/lib/api/client'
import { formatCurrency } from '@/lib/utils'

export default function DashboardPage() {
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
      console.error('Failed to load dashboard data:', err)
      setError('Gagal memuat ringkasan dashboard. Coba refresh kembali.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const lowStockCount = products.filter((product) => product.is_low_stock).length
  const inventoryValue = products.reduce(
    (sum, product) => sum + Number(product.unit_price || 0) * Number(product.stock_quantity || 0),
    0
  )
  const unpaidInvoices = invoices.filter(
    (invoice) => invoice.payment_status === 'unpaid' || invoice.payment_status === 'overdue'
  )
  const paidRevenue = invoices
    .filter((invoice) => invoice.payment_status === 'paid')
    .reduce((sum, invoice) => sum + Number(invoice.total_amount || 0), 0)

  const recentInvoices = [...invoices]
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
    .slice(0, 5)

  return (
    <div className="space-y-6">
      <PageHeader
        label="Operations"
        title="Dashboard"
        description="Snapshot performa operasional inventory dan invoicing."
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

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Produk Aktif" value={products.length} subtitle="produk siap jual" />
        <StatCard
          title="Low Stock"
          value={lowStockCount}
          subtitle="produk butuh restock"
          tone="warning"
        />
        <StatCard
          title="Invoice Belum Bayar"
          value={unpaidInvoices.length}
          subtitle="status unpaid atau overdue"
          tone="danger"
        />
        <StatCard
          title="Revenue Terkonfirmasi"
          value={formatCurrency(paidRevenue)}
          subtitle="dari invoice paid"
          tone="success"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Invoice Terbaru</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <p className="text-sm text-muted-foreground">Memuat data invoice...</p>
            ) : recentInvoices.length === 0 ? (
              <p className="text-sm text-muted-foreground">Belum ada invoice.</p>
            ) : (
              <div className="space-y-3">
                {recentInvoices.map((invoice) => (
                  <div
                    key={invoice.id}
                    className="flex items-center justify-between rounded-xl border border-border/80 bg-background/70 px-3 py-3"
                  >
                    <div>
                      <p className="font-medium text-foreground">{invoice.invoice_number}</p>
                      <p className="text-sm text-muted-foreground">{invoice.customer_name}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold text-foreground">
                        {formatCurrency(invoice.total_amount)}
                      </p>
                      <Badge
                        variant={
                          invoice.payment_status === 'paid'
                            ? 'default'
                            : invoice.payment_status === 'overdue'
                              ? 'destructive'
                              : 'secondary'
                        }
                      >
                        {invoice.payment_status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Quick Access</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link href="/inventory" className="block">
              <Button variant="outline" className="w-full justify-start gap-2">
                <Package className="h-4 w-4" />
                Kelola Inventory
              </Button>
            </Link>
            <Link href="/invoices" className="block">
              <Button variant="outline" className="w-full justify-start gap-2">
                <FileText className="h-4 w-4" />
                Kelola Invoice
              </Button>
            </Link>
            <Link href="/chat" className="block">
              <Button variant="outline" className="w-full justify-start gap-2">
                <MessageSquare className="h-4 w-4" />
                Tanya AI Assistant
              </Button>
            </Link>
            <Link href="/analytics" className="block">
              <Button variant="outline" className="w-full justify-start gap-2">
                <BarChart3 className="h-4 w-4" />
                Buka Analytics
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Nilai Inventory</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-3xl font-semibold text-foreground">{formatCurrency(inventoryValue)}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Total estimasi nilai stok dari {products.length} produk aktif.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
