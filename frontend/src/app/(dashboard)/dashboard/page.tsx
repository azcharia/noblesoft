/**
 * Dashboard Page
 * High-level business snapshot with integrated AI chat cash register for UMKM.
 */
'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { FileText, MessageSquare, Package, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PageAlert } from '@/components/dashboard/PageAlert'
import { PageHeader } from '@/components/dashboard/PageHeader'
import { StatCard } from '@/components/dashboard/StatCard'
import { apiClient, type Invoice, type Product } from '@/lib/api/client'
import { formatCurrency } from '@/lib/utils'
import { ChatInterface } from '@/components/chat/ChatInterface'

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
  const outOfStockCount = products.filter((product) => Number(product.stock_quantity || 0) === 0).length
  
  const paidRevenue = invoices
    .filter((invoice) => invoice.payment_status === 'paid')
    .reduce((sum, invoice) => sum + Number(invoice.total_amount || 0), 0)

  const estimatedProfit = paidRevenue * 0.30 // 30% profit margin estimation for small businesses

  const recentInvoices = [...invoices]
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
    .slice(0, 5)

  return (
    <div className="space-y-6">
      <PageHeader
        label="Kasir Digital & Stok"
        title="Halaman Utama"
        description="Pantau penjualan, stok barang, dan gunakan asisten kasir pintar Anda."
        actions={
          <Button
            variant="outline"
            className="w-full gap-2 sm:w-auto"
            onClick={loadData}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Muat Ulang Data
          </Button>
        }
      />

      {error ? <PageAlert message={error} variant="error" /> : null}

      {/* 3 Kartu Kas Keuangan Minimalis */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard
          className="glass-card border-none shadow-sm"
          title="Pendapatan Lunas"
          value={formatCurrency(paidRevenue)}
          subtitle="Total uang masuk dari nota yang lunas"
          tone="success"
        />
        <StatCard
          className="glass-card border-none shadow-sm"
          title="Perkiraan Untung Bersih"
          value={formatCurrency(estimatedProfit)}
          subtitle="Perkiraan untung hari ini (asumsi margin 30%)"
          tone="accent"
        />
        <StatCard
          className="glass-card border-none shadow-sm"
          title="Stok Barang Habis"
          value={outOfStockCount}
          subtitle={`${lowStockCount} produk perlu segera ditambah`}
          tone={outOfStockCount > 0 ? 'danger' : 'default'}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Asisten AI Kasir Terintegrasi */}
        <Card className="xl:col-span-2 flex flex-col h-[600px] overflow-hidden glass-card border-none shadow-sm">
          <CardHeader className="pb-3 border-b border-border bg-muted/20">
            <CardTitle className="text-lg flex items-center gap-2 text-brand-teal">
              <MessageSquare className="w-5 h-5 text-brand-blue" />
              Asisten AI Kasir (Tanya Jawab Stok & Nota)
            </CardTitle>
          </CardHeader>
          <div className="flex-1 flex flex-col min-h-0 overflow-hidden p-4">
            <ChatInterface noBorder />
          </div>
        </Card>

        {/* Info Samping: Invoices & Quick Access */}
        <div className="space-y-6 xl:col-span-1">
          <Card className="glass-card border-none shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg text-brand-teal">Nota Penjualan Terbaru</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <p className="text-sm text-muted-foreground">Memuat data nota...</p>
              ) : recentInvoices.length === 0 ? (
                <p className="text-sm text-muted-foreground">Belum ada catatan penjualan.</p>
              ) : (
                <div className="space-y-3">
                  {recentInvoices.map((invoice) => (
                    <div
                      key={invoice.id}
                      className="flex items-center justify-between rounded-xl border border-border bg-background/50 px-3 py-3"
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
                          {invoice.payment_status === 'paid' ? 'Lunas' : invoice.payment_status === 'overdue' ? 'Jatuh Tempo' : 'Pending'}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="glass-card border-none shadow-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg text-brand-teal">Menu Akses Cepat</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Link href="/inventory" className="block">
                <Button variant="outline" className="w-full justify-start gap-2">
                  <Package className="h-4 w-4 text-muted-foreground" />
                  Atur Stok Barang
                </Button>
              </Link>
              <Link href="/invoices" className="block">
                <Button variant="outline" className="w-full justify-start gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  Kelola Nota Pembeli
                </Button>
              </Link>
              <Link href="/chat" className="block">
                <Button variant="outline" className="w-full justify-start gap-2">
                  <MessageSquare className="h-4 w-4 text-muted-foreground" />
                  Buka Chat AI (Layar Penuh)
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
