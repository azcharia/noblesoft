/**
 * Inventory Page
 * Displays and manages products
 */
'use client'

import { useState, useEffect, useCallback } from 'react'
import { Plus, Search, Filter, AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
import { apiClient, type Product } from '@/lib/api/client'
import { formatCurrency } from '@/lib/utils'

export default function InventoryPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formState, setFormState] = useState({
    sku: '',
    name: '',
    description: '',
    category: '',
    unit_price: '0',
    stock_quantity: '0',
    low_stock_threshold: '10',
  })
  
  const loadProducts = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await apiClient.products.list({
        page,
        page_size: 20,
        search: search || undefined,
        is_active: true,
      })
      
      setProducts(data.products)
      setTotal(data.total)
      setHasMore(data.has_more)
    } catch (error) {
      console.error('Failed to load products:', error)
      setError('Gagal memuat produk. Coba refresh kembali.')
    } finally {
      setIsLoading(false)
    }
  }, [page, search])

  useEffect(() => {
    loadProducts()
  }, [loadProducts])
  
  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1) // Reset to first page
  }

  const resetForm = () => {
    setFormState({
      sku: '',
      name: '',
      description: '',
      category: '',
      unit_price: '0',
      stock_quantity: '0',
      low_stock_threshold: '10',
    })
    setEditingId(null)
  }

  const openCreateForm = () => {
    setShowCreateForm((prev) => {
      const next = !prev
      if (next) {
        resetForm()
      }
      return next
    })
  }

  const openEditForm = (product: Product) => {
    setShowCreateForm(true)
    setEditingId(product.id)
    setFormState({
      sku: product.sku,
      name: product.name,
      description: product.description || '',
      category: product.category || '',
      unit_price: String(product.unit_price),
      stock_quantity: String(product.stock_quantity),
      low_stock_threshold: String(product.low_stock_threshold),
    })
  }

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      const payload = {
        sku: formState.sku.trim(),
        name: formState.name.trim(),
        description: formState.description.trim() || undefined,
        category: formState.category.trim() || undefined,
        unit_price: Number(formState.unit_price),
        stock_quantity: Number(formState.stock_quantity),
        low_stock_threshold: Number(formState.low_stock_threshold),
        is_active: true,
      }

      if (!payload.sku || !payload.name) {
        throw new Error('SKU dan nama produk wajib diisi.')
      }

      if (Number.isNaN(payload.unit_price) || Number.isNaN(payload.stock_quantity)) {
        throw new Error('Unit price dan stock quantity harus berupa angka valid.')
      }

      if (editingId) {
        await apiClient.products.update(editingId, payload)
      } else {
        await apiClient.products.create(payload)
      }

      resetForm()
      setShowCreateForm(false)
      await loadProducts()
    } catch (err) {
      console.error('Failed to submit product form:', err)
      setError(err instanceof Error ? err.message : 'Gagal menyimpan data produk.')
    } finally {
      setIsSubmitting(false)
    }
  }
  
  return (
    <div className="space-y-6">
      <PageHeader
        label="Persediaan Stok"
        title="Stok Barang"
        description="Atur daftar barang dagangan Anda dan pantau jumlah persediaan stok agar tidak kehabisan."
        actions={
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
            <Button
              variant="outline"
              className="w-full gap-2 sm:w-auto"
              onClick={loadProducts}
              disabled={isLoading}
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              Muat Ulang
            </Button>
            <Button className="w-full gap-2 sm:w-auto bg-brand-orange hover:bg-brand-orange/90 text-white border-none shadow-sm" onClick={openCreateForm}>
              <Plus className="w-4 h-4" />
              {showCreateForm && !editingId ? 'Tutup Formulir' : '+ Tambah Barang Baru'}
            </Button>
          </div>
        }
      />

      {error ? <PageAlert message={error} variant="error" /> : null}

      {showCreateForm && (
        <Card>
          <form onSubmit={handleSubmit}>
            <CardHeader className="flex flex-row items-center justify-between gap-4 space-y-0">
              <CardTitle>{editingId ? 'Ubah Detail Barang' : 'Tambah Barang Baru'}</CardTitle>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => {
                  setShowCreateForm(false)
                  resetForm()
                }}
              >
                Batal
              </Button>
            </CardHeader>

            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>SKU / Kode Barang <span className="text-destructive">*</span></Label>
                  <Input
                    placeholder="Contoh: KB-001"
                    value={formState.sku}
                    onChange={(e) => setFormState((prev) => ({ ...prev, sku: e.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Nama Barang <span className="text-destructive">*</span></Label>
                  <Input
                    placeholder="Contoh: Kain Batik Solo"
                    value={formState.name}
                    onChange={(e) => setFormState((prev) => ({ ...prev, name: e.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Kategori Barang</Label>
                  <Input
                    placeholder="Contoh: Batik, Makanan, dll"
                    value={formState.category}
                    onChange={(e) => setFormState((prev) => ({ ...prev, category: e.target.value }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Harga Satuan <span className="text-destructive">*</span></Label>
                  <Input
                    type="text"
                    placeholder="Rp 0"
                    value={formState.unit_price !== '0' && formState.unit_price !== '' ? new Intl.NumberFormat('id-ID').format(Number(formState.unit_price)) : formState.unit_price === '0' ? '' : formState.unit_price}
                    onChange={(e) => {
                      const rawValue = e.target.value.replace(/\D/g, '')
                      setFormState((prev) => ({ ...prev, unit_price: rawValue || '0' }))
                    }}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Sisa Stok <span className="text-destructive">*</span></Label>
                  <Input
                    type="number"
                    min="0"
                    placeholder="Jumlah Stok"
                    value={formState.stock_quantity}
                    onChange={(e) => setFormState((prev) => ({ ...prev, stock_quantity: e.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Batas Stok Minimum Peringatan</Label>
                  <Input
                    type="number"
                    min="0"
                    placeholder="Batas Minimum"
                    value={formState.low_stock_threshold}
                    onChange={(e) =>
                      setFormState((prev) => ({
                        ...prev,
                        low_stock_threshold: e.target.value,
                      }))
                    }
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Deskripsi Barang (Opsional)</Label>
                <Textarea
                  placeholder="Keterangan tambahan barang..."
                  value={formState.description}
                  onChange={(e) => setFormState((prev) => ({ ...prev, description: e.target.value }))}
                />
              </div>

              <Button type="submit" disabled={isSubmitting} className="gap-2 w-full md:w-auto mt-4 bg-brand-teal text-white hover:bg-brand-teal/90 border-none shadow-sm">
                {isSubmitting ? 'Menyimpan...' : editingId ? 'Simpan Perubahan' : 'Tambah Barang Dagangan'}
              </Button>
            </CardContent>
          </form>
        </Card>
      )}
      
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Cari barang berdasarkan nama, kode barang (SKU), atau keterangan..."
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button variant="outline" className="gap-2">
          <Filter className="w-4 h-4" />
          Penyaring
        </Button>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard title="Total Jenis Barang" value={total} />
        <StatCard
          title="Barang Hampir Habis"
          value={products.filter((p) => p.is_low_stock).length}
          tone="warning"
        />
        <StatCard
          title="Nilai Total Stok"
          value={formatCurrency(products.reduce((sum, p) => sum + p.unit_price * p.stock_quantity, 0))}
        />
        <StatCard
          title="Total Kategori"
          value={new Set(products.map((p) => p.category).filter(Boolean)).size}
        />
      </div>
      
      {/* Table */}
      <div className="overflow-hidden rounded-2xl">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Kode Barang (SKU)</TableHead>
              <TableHead>Nama Barang</TableHead>
              <TableHead>Kategori</TableHead>
              <TableHead className="text-right">Harga Jual</TableHead>
              <TableHead className="text-right">Sisa Stok</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Aksi</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  Memuat data barang...
                </TableCell>
              </TableRow>
            ) : products.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                  Barang tidak ditemukan
                </TableCell>
              </TableRow>
            ) : (
              products.map((product) => (
                <TableRow key={product.id}>
                  <TableCell className="font-mono text-sm">
                    {product.sku}
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium text-foreground">{product.name}</p>
                      {product.description && (
                        <p className="text-sm text-muted-foreground line-clamp-1">
                          {product.description}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {product.category && (
                      <Badge variant="outline">{product.category}</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right font-medium">
                    {formatCurrency(product.unit_price)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <span className={product.is_low_stock ? 'text-amber-600 font-medium' : ''}>
                        {product.stock_quantity}
                      </span>
                      {product.is_low_stock && (
                        <AlertTriangle className="w-4 h-4 text-amber-600" />
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {product.is_low_stock ? (
                      <Badge variant="destructive">Hampir Habis</Badge>
                    ) : (
                      <Badge variant="default">Tersedia</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => openEditForm(product)}
                      className="text-brand-teal hover:text-brand-blue"
                    >
                      Ubah Detail
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        
        {/* Pagination */}
        {!isLoading && products.length > 0 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-border">
            <p className="text-sm text-muted-foreground">
              Menampilkan {(page - 1) * 20 + 1} sampai {Math.min(page * 20, total)} dari {total} barang
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Sebelumnya
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={!hasMore}
              >
                Berikutnya
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
