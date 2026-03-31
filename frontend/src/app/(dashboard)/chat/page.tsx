/**
 * AI Chat Page
 * Conversational AI interface for Pro/Enterprise users
 */
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { Lock } from 'lucide-react'
import { createClient } from '@/lib/supabase/server'
import { ChatInterface } from '@/components/chat/ChatInterface'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/dashboard/PageHeader'

export default async function ChatPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    redirect('/login')
  }
  
  // Fetch user with tenant info
  const { data: userData } = await supabase
    .from('users')
    .select(`
      *,
      tenants (
        subscription_tier
      )
    `)
    .eq('id', user.id)
    .single()
  
  const tenant = (userData as any)?.tenants
  const subscriptionTier = tenant?.subscription_tier
  
  // Check if user has access to AI Chat
  if (!['pro', 'enterprise'].includes(subscriptionTier)) {
    return (
      <div className="flex h-full items-center justify-center">
        <Card className="w-full max-w-xl">
          <CardHeader className="items-center text-center">
            <div className="mb-2 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-accent-horizontal shadow-accent">
              <Lock className="h-8 w-8 text-primary-foreground" />
            </div>
            <CardTitle className="text-2xl">AI Assistant - Pro Feature</CardTitle>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-muted-foreground">
              Upgrade to Pro or Enterprise to access the AI Assistant and unlock powerful conversational analytics for your business.
            </p>
            <div className="mt-6">
              <Link href="/settings/billing">
                <Button className="w-full sm:w-auto">Upgrade to Pro</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }
  
  return (
    <div className="h-full flex flex-col gap-6">
      <PageHeader
        label="AI Workspace"
        title="AI Assistant"
        description="Ask questions about your inventory, invoices, and business data."
      />

      <ChatInterface />
    </div>
  )
}
