/**
 * Operations Support Page
 * Internal support ticketing and SLA tracking.
 */
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { PageAlert } from '@/components/dashboard/PageAlert'
import { PageHeader } from '@/components/dashboard/PageHeader'
import { SupportPanel } from '@/components/dashboard/SupportPanel'
import { Button } from '@/components/ui/button'

export default async function OperationsSupportPage() {
  const supabase = createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    redirect('/login')
  }

  const { data: userData } = await supabase
    .from('users')
    .select(
      `
      id,
      role,
      tenants (
        subscription_tier
      )
    `
    )
    .eq('id', user.id)
    .single()

  const currentUserRole = (userData as any)?.role as string | undefined
  const subscriptionTier = (userData as any)?.tenants?.subscription_tier as string | undefined

  if (!currentUserRole) {
    redirect('/settings')
  }

  if (currentUserRole !== 'owner' && currentUserRole !== 'admin') {
    redirect('/settings')
  }

  const hasEnterpriseAccess = subscriptionTier === 'enterprise'

  return (
    <div className="space-y-6">
      <PageHeader
        label="Operations"
        title="Support"
        description="Internal support ticketing dengan SLA response dan resolution tracking."
      />

      {!hasEnterpriseAccess ? (
        <div className="space-y-4">
          <PageAlert
            variant="warning"
            message="Support ticketing memerlukan subscription Enterprise."
          />
          <Link href="/settings/billing">
            <Button>Upgrade ke Enterprise</Button>
          </Link>
        </div>
      ) : (
        <ErrorBoundary>
          <SupportPanel />
        </ErrorBoundary>
      )}
    </div>
  )
}
