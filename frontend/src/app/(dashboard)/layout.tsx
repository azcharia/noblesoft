/**
 * Dashboard Layout
 * Sidebar navigation with subscription tier enforcement
 */
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { OfflineBanner } from '@/components/OfflineBanner'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // Check authentication
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
        id,
        company_name,
        subscription_tier,
        is_active,
        trial_end_date,
        max_users
      )
    `)
    .eq('id', user.id)
    .single()

  const userWithTenant = userData as any
  
  if (!userWithTenant || !userWithTenant.tenants) {
    redirect('/login')
  }
  
  const tenant = userWithTenant.tenants as any
  
  // Check if tenant is active
  if (!tenant.is_active) {
    redirect('/suspended')
  }
  
  // Check trial expiration
  if (tenant.subscription_tier === 'trial' && tenant.trial_end_date) {
    const trialEnd = new Date(tenant.trial_end_date)
    if (trialEnd < new Date()) {
      redirect('/trial-expired')
    }
  }
  
  return (
    <>
      <OfflineBanner />
      <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar
        user={userWithTenant}
        tenant={tenant}
        subscriptionTier={tenant.subscription_tier}
      />
      
      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header
          user={userWithTenant}
          companyName={tenant.company_name}
          subscriptionTier={tenant.subscription_tier}
        />
        
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
      </div>
    </>
  )
}
