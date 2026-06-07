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
  return (
    <>
      <OfflineBanner />
      <div className="flex h-screen bg-background relative overflow-hidden">
        {/* Glassmorphic decorative glowing blobs */}
        <div className="absolute top-[-10%] left-[-10%] w-[45vw] h-[45vw] rounded-full bg-gradient-to-br from-brand-teal/10 to-transparent blur-[130px] pointer-events-none z-0" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[45vw] h-[45vw] rounded-full bg-gradient-to-tr from-brand-blue/8 to-transparent blur-[130px] pointer-events-none z-0" />
        <div className="absolute top-[35%] right-[15%] w-[25vw] h-[25vw] rounded-full bg-gradient-to-l from-brand-blue/4 to-transparent blur-[90px] pointer-events-none z-0" />

        {/* Sidebar */}
        <Sidebar
          key={`sidebar-${userWithTenant.id}`}
          user={userWithTenant}
          tenant={tenant}
        />
        
        {/* Main content */}
        <div className="flex-1 flex flex-col overflow-hidden relative z-10">
          <Header
            key={`header-${userWithTenant.id}`}
            user={userWithTenant}
            companyName={tenant.company_name}
          />
          
          <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
            {children}
          </main>
        </div>
      </div>
    </>
  )
}
