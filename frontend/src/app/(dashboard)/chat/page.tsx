/**
 * AI Chat Page
 * Conversational AI interface for all users
 */
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { ChatInterface } from '@/components/chat/ChatInterface'
import { PageHeader } from '@/components/dashboard/PageHeader'

export default async function ChatPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    redirect('/login')
  }
  
  return (
    <div className="h-[calc(100vh-150px)] lg:h-[calc(100vh-175px)] min-h-[400px] flex flex-col gap-4 overflow-hidden">
      <PageHeader
        label="Asisten Pintar"
        title="Obrolan AI Toko"
        description="Tanya tentang persediaan stok barang, penjualan, nota keuangan, atau analisis data toko Anda secara langsung."
      />

      <div className="flex-1 min-h-0 overflow-hidden bg-white/30 backdrop-blur-md rounded-2xl border border-border/50 p-4 flex flex-col">
        <ChatInterface noBorder />
      </div>
    </div>
  )
}
