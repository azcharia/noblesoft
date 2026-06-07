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
    <div className="flex-1 flex flex-col gap-3 overflow-hidden">
      <div className="flex-shrink-0">
        <PageHeader
          label="Asisten Pintar"
          title="Obrolan AI Toko"
          description="Tanya tentang stok, penjualan, atau analisis data toko Anda."
        />
      </div>

      <div className="flex-1 min-h-0 bg-card/50 backdrop-blur-sm rounded-2xl border border-border flex flex-col overflow-hidden">
        <ChatInterface noBorder />
      </div>
    </div>
  )
}
