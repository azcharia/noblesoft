'use client'

import { useState, useEffect, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Save, Plus, Trash2 } from 'lucide-react'
import Link from 'next/link'
import CreatableSelect from 'react-select/creatable'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PageHeader } from '@/components/dashboard/PageHeader'
import { PageAlert } from '@/components/dashboard/PageAlert'
import { apiClient, type Product } from '@/lib/api/client'
import { formatCurrency } from '@/lib/utils'

export default function NewInvoicePage() {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const [products, setProducts] = useState<Product[]>([])
  const [isLoadingProducts, setIsLoadingProducts] = useState(true)

  const [customerName, setCustomerName] = useState('')
  const [customerEmail, setCustomerEmail] = useState('')
  const [customerPhone, setCustomerPhone] = useState('')
  const [issueDate, setIssueDate] = useState(new Date().toISOString().split('T')[0])
  const [dueDate, setDueDate] = useState('')
  const [notes, setNotes] = useState('')
  
  const [items, setItems] = useState<Array<{
    product_id: string
    description: string
    quantity: number
    unit_price: number
  }>>([
    { product_id: '', description: '', quantity: 1, unit_price: 0 }
  ])

  useEffect(() => {
    async function loadProducts() {
      try {
        const data = await apiClient.products.list({ page_size: 100 })
        setProducts(data.products)
      } catch (err) {
        console.error('Failed to load products:', err)
      } finally {
        setIsLoadingProducts(false)
      }
    }
    loadProducts()
  }, [])

  const handleAddItem = () => {
    setItems([...items, { product_id: '', description: '', quantity: 1, unit_price: 0 }])
  }

  const handleRemoveItem = (index: number) => {
    const newItems = [...items]
    newItems.splice(index, 1)
    setItems(newItems)
  }

  const handleItemChange = (index: number, field: string, value: any) => {
    const newItems = [...items]
    
    if (field === 'clear') {
      newItems[index].product_id = ''
      newItems[index].description = ''
      newItems[index].unit_price = 0
    } else if (field === 'custom') {
      newItems[index].product_id = ''
      newItems[index].description = value
    } else if (field === 'product') {
      newItems[index].product_id = value.id
      newItems[index].description = value.name
      newItems[index].unit_price = value.unit_price
    } else {
      (newItems[index] as any)[field] = value
    }
    
    setItems(newItems)
  }

  const productOptions = useMemo(() => {
    return products.map(p => ({
      value: p.id,
      label: `${p.name} - ${formatCurrency(p.unit_price)}`,
      product: p
    }))
  }, [products])

  const { subtotal, taxAmount, totalAmount } = useMemo(() => {
    const sub = items.reduce((acc, item) => acc + (item.quantity * item.unit_price), 0)
    const tax = sub * 0.11 // 11% PPN
    return {
      subtotal: sub,
      taxAmount: tax,
      totalAmount: sub + tax
    }
  }, [items])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!customerName) {
      setError('Nama pelanggan wajib diisi.')
      return
    }

    if (items.some(item => !item.description || item.quantity <= 0)) {
      setError('Pastikan semua item memiliki deskripsi dan jumlah yang valid.')
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)

      const invoiceNumber = `INV-${new Date().getFullYear()}${(new Date().getMonth()+1).toString().padStart(2, '0')}-${Math.floor(Math.random() * 1000).toString().padStart(3, '0')}`

      await apiClient.invoices.create({
        invoice_number: invoiceNumber,
        customer_name: customerName,
        customer_email: customerEmail || undefined,
        customer_phone: customerPhone || undefined,
        issue_date: issueDate,
        due_date: dueDate || undefined,
        tax_amount: taxAmount,
        notes: notes || undefined,
        items: items.map(item => ({
          product_id: item.product_id || undefined,
          description: item.description,
          quantity: item.quantity,
          unit_price: item.unit_price
        }))
      })

      router.push('/invoices')
      router.refresh()
    } catch (err: any) {
      console.error('Failed to create invoice:', err)
      setError(err.message || 'Gagal membuat tagihan.')
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-6 pb-20">
      <div className="flex items-center gap-4">
        <Link href="/invoices">
          <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <PageHeader
          label="Penjualan & Kasir"
          title="Buat Tagihan Baru"
          description="Catat tagihan dan nota baru untuk pelanggan Anda."
        />
      </div>

      {error && <PageAlert message={error} variant="error" />}

      <form onSubmit={handleSubmit} className="space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-card p-6 rounded-xl shadow-sm border border-border">
          <div className="space-y-4">
            <h3 className="font-semibold text-lg">Informasi Pelanggan</h3>
            
            <div className="space-y-2">
              <Label>Nama Pelanggan <span className="text-destructive">*</span></Label>
              <Input 
                value={customerName}
                onChange={e => setCustomerName(e.target.value)}
                placeholder="Misal: Bapak Budi / PT Maju Jaya"
                required
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Email</Label>
                <Input 
                  type="email"
                  value={customerEmail}
                  onChange={e => setCustomerEmail(e.target.value)}
                  placeholder="budi@example.com"
                />
              </div>
              <div className="space-y-2">
                <Label>No. Telepon</Label>
                <Input 
                  value={customerPhone}
                  onChange={e => setCustomerPhone(e.target.value)}
                  placeholder="0812..."
                />
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="font-semibold text-lg">Informasi Tagihan</h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Tanggal Terbit <span className="text-destructive">*</span></Label>
                <Input 
                  type="date"
                  value={issueDate}
                  onChange={e => setIssueDate(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Jatuh Tempo</Label>
                <Input 
                  type="date"
                  value={dueDate}
                  onChange={e => setDueDate(e.target.value)}
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Catatan (Opsional)</Label>
              <Input 
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder="Terima kasih atas pembelian Anda..."
              />
            </div>
          </div>
        </div>

        <div className="bg-card p-6 rounded-xl shadow-sm border border-border space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-lg">Daftar Barang</h3>
            <Button type="button" variant="outline" size="sm" onClick={handleAddItem} className="gap-2">
              <Plus className="h-4 w-4" />
              Tambah Baris
            </Button>
          </div>

          <div className="space-y-4">
            {items.map((item, index) => (
              <div key={index} className="flex flex-col md:flex-row gap-4 items-start md:items-end border-b border-border pb-4 last:border-0 last:pb-0">
                <div className="flex-1 w-full space-y-2">
                  <Label>Pilih Produk / Deskripsi</Label>
                  <CreatableSelect
                    isClearable
                    placeholder="Ketik nama produk untuk mencari atau isi manual..."
                    options={productOptions}
                    value={item.product_id 
                      ? productOptions.find(o => o.value === item.product_id) 
                      : item.description 
                        ? { value: item.description, label: item.description, product: null } 
                        : null}
                    onChange={(newValue: any) => {
                      if (!newValue) {
                         handleItemChange(index, 'clear', null)
                      } else if (newValue.__isNew__) {
                         handleItemChange(index, 'custom', newValue.value)
                      } else {
                         handleItemChange(index, 'product', newValue.product)
                      }
                    }}
                    formatCreateLabel={(inputValue) => `Tambahkan "${inputValue}"`}
                    styles={{
                      control: (base) => ({
                        ...base,
                        minHeight: '2.5rem',
                        borderRadius: '0.375rem',
                        borderColor: 'hsl(var(--input))',
                        boxShadow: 'none',
                        '&:hover': {
                          borderColor: 'hsl(var(--ring))'
                        }
                      }),
                      menu: (base) => ({
                        ...base,
                        zIndex: 50
                      })
                    }}
                  />
                </div>
                
                <div className="w-full md:w-32 space-y-2">
                  <Label>Harga Satuan</Label>
                  <Input 
                    type="number"
                    min="0"
                    value={item.unit_price}
                    onChange={e => handleItemChange(index, 'unit_price', parseFloat(e.target.value) || 0)}
                  />
                </div>

                <div className="w-full md:w-24 space-y-2">
                  <Label>Qty</Label>
                  <Input 
                    type="number"
                    min="1"
                    value={item.quantity}
                    onChange={e => handleItemChange(index, 'quantity', parseInt(e.target.value) || 1)}
                  />
                </div>

                <div className="w-full md:w-40 space-y-2">
                  <Label>Subtotal</Label>
                  <div className="h-10 flex items-center px-3 bg-muted/50 rounded-md border border-input font-medium">
                    {formatCurrency(item.quantity * item.unit_price)}
                  </div>
                </div>

                <Button 
                  type="button" 
                  variant="ghost" 
                  size="icon" 
                  className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  onClick={() => handleRemoveItem(index)}
                  disabled={items.length <= 1}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col md:flex-row gap-6 justify-end items-start md:items-center">
          <div className="bg-card p-6 rounded-xl shadow-sm border border-border w-full md:w-80 space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Subtotal</span>
              <span className="font-medium">{formatCurrency(subtotal)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">PPN (11%)</span>
              <span className="font-medium">{formatCurrency(taxAmount)}</span>
            </div>
            <div className="border-t border-border pt-3 flex justify-between">
              <span className="font-semibold">Total Tagihan</span>
              <span className="font-bold text-lg text-brand-orange">{formatCurrency(totalAmount)}</span>
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-4">
          <Link href="/invoices">
            <Button type="button" variant="outline">Batal</Button>
          </Link>
          <Button type="submit" className="gap-2 bg-brand-orange hover:bg-brand-orange/90 text-white border-none shadow-sm" disabled={isSubmitting}>
            {isSubmitting ? 'Menyimpan...' : (
              <>
                <Save className="h-4 w-4" />
                Simpan Tagihan
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
