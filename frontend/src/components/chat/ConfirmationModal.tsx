/**
 * Confirmation Modal Component
 * Double confirmation for sensitive transactions
 */
'use client'

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ArrowRight, CheckCircle2, XCircle, Info } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ConfirmationData {
  action_type: 'sell' | 'restock' | 'debt' | 'check'
  item_name: string
  quantity: number
  unit_name?: string
  price_per_item: number
  total_price: number
  customer_name?: string
  payment_status: 'paid' | 'unpaid'
  stock_before: number
  stock_after: number
}

interface ConfirmationModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  data: ConfirmationData | null
}

export function ConfirmationModal({ isOpen, onClose, onConfirm, data }: ConfirmationModalProps) {
  if (!data) return null

  const getActionConfig = () => {
    switch (data.action_type) {
      case 'sell':
        return {
          title: 'Konfirmasi Penjualan',
          color: 'bg-emerald-600',
          textColor: 'text-emerald-700',
          borderColor: 'border-emerald-200',
          bgColor: 'bg-emerald-50',
          icon: <CheckCircle2 className="w-6 h-6 text-emerald-600" />
        }
      case 'restock':
        return {
          title: 'Konfirmasi Tambah Stok',
          color: 'bg-blue-600',
          textColor: 'text-blue-700',
          borderColor: 'border-blue-200',
          bgColor: 'bg-blue-50',
          icon: <Info className="w-6 h-6 text-blue-600" />
        }
      case 'debt':
        return {
          title: 'Konfirmasi Catat Utang',
          color: 'bg-amber-600',
          textColor: 'text-amber-700',
          borderColor: 'border-amber-200',
          bgColor: 'bg-amber-50',
          icon: <Info className="w-6 h-6 text-amber-600" />
        }
      default:
        return {
          title: 'Konfirmasi Aksi',
          color: 'bg-slate-600',
          textColor: 'text-slate-700',
          borderColor: 'border-slate-200',
          bgColor: 'bg-slate-50',
          icon: <Info className="w-6 h-6 text-slate-600" />
        }
    }
  }

  const config = getActionConfig()
  const formatIDR = (amount: number) => {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      minimumFractionDigits: 0
    }).format(amount)
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg border-none p-0 overflow-hidden rounded-3xl">
        {/* Header with Background Color */}
        <div className={cn("p-6 text-white flex items-center gap-3", config.color)}>
          {config.icon && <div className="bg-white/20 p-2 rounded-xl">{config.icon}</div>}
          <DialogHeader>
            <DialogTitle className="text-2xl font-black text-white">{config.title}</DialogTitle>
          </DialogHeader>
        </div>

        <div className="p-8 space-y-8 bg-white">
          {/* Main Info Card */}
          <div className={cn("rounded-2xl border-2 p-5 space-y-4", config.borderColor, config.bgColor)}>
            <div className="flex justify-between items-start">
              <div className="space-y-1">
                <p className="text-sm font-bold text-slate-500 uppercase tracking-wider">Nama Barang</p>
                <p className="text-2xl font-black text-slate-900">{data.item_name}</p>
              </div>
              <Badge className={cn("px-4 py-1.5 text-sm font-black uppercase", 
                data.payment_status === 'paid' ? "bg-emerald-600" : "bg-amber-600"
              )}>
                {data.payment_status === 'paid' ? 'LUNAS (TUNAI)' : 'BELUM BAYAR (UTANG)'}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-6 pt-2">
              <div className="space-y-1">
                <p className="text-sm font-bold text-slate-500 uppercase tracking-wider">Jumlah</p>
                <p className="text-xl font-black text-slate-900">
                  {data.quantity} {data.unit_name || 'pcs'}
                </p>
              </div>
              {data.customer_name && (
                <div className="space-y-1 text-right">
                  <p className="text-sm font-bold text-slate-500 uppercase tracking-wider">Pelanggan</p>
                  <p className="text-xl font-black text-slate-900">{data.customer_name}</p>
                </div>
              )}
            </div>
          </div>

          {/* Stock Change Visualizer */}
          <div className="flex items-center justify-between px-2">
            <div className="text-center space-y-1">
              <p className="text-xs font-black text-slate-400 uppercase">Stok Awal</p>
              <p className="text-xl font-black text-slate-500">{data.stock_before} {data.unit_name || 'pcs'}</p>
            </div>
            
            <div className="flex flex-col items-center gap-1">
              <div className={cn("px-3 py-1 rounded-lg text-xs font-black text-white", config.color)}>
                {data.action_type === 'restock' ? `+${data.quantity}` : `-${data.quantity}`}
              </div>
              <ArrowRight className="w-8 h-8 text-slate-300" />
            </div>

            <div className="text-center space-y-1">
              <p className="text-xs font-black text-slate-400 uppercase">Stok Akhir</p>
              <p className={cn("text-2xl font-black", config.textColor)}>
                {data.stock_after} {data.unit_name || 'pcs'}
              </p>
            </div>
          </div>

          {/* Grand Total Section */}
          <div className="pt-4 border-t-2 border-slate-100 flex flex-col items-center">
            <p className="text-sm font-bold text-slate-500 uppercase mb-1">Total yang Harus Dibayar</p>
            <p className="text-4xl md:text-5xl font-black text-slate-900 tracking-tighter">
              {formatIDR(data.total_price)}
            </p>
            <p className="text-sm font-bold text-slate-400 mt-1">
              ({data.quantity} x {formatIDR(data.price_per_item)})
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <DialogFooter className="p-6 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row gap-3">
          <Button
            variant="ghost"
            onClick={onClose}
            className="flex-1 h-14 text-lg font-bold text-slate-500 hover:bg-slate-200 rounded-2xl"
          >
            <XCircle className="w-5 h-5 mr-2" />
            BATAL / UBAH
          </Button>
          <Button
            onClick={onConfirm}
            className={cn("flex-1 h-14 text-lg font-black text-white shadow-lg rounded-2xl active:scale-95 transition-transform", config.color)}
          >
            <CheckCircle2 className="w-5 h-5 mr-2" />
            YA, SUDAH BENAR
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
