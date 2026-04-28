/**
 * Operations Onboarding Page
 * Enterprise onboarding checklist and setup progress.
 */
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { OnboardingPanel } from '@/components/dashboard/OnboardingPanel'
import { PageAlert } from '@/components/dashboard/PageAlert'
import { PageHeader } from '@/components/dashboard/PageHeader'
import { Button } from '@/components/ui/button'

export default async function OperationsOnboardingPage() {
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
        title="Onboarding"
        description="Guided setup checklist untuk tenant baru agar go-live lebih cepat."
      />

      {!hasEnterpriseAccess ? (
        <div className="space-y-4">
          <PageAlert
            variant="warning"
            message="Onboarding checklist memerlukan subscription Enterprise."
          />
          <Link href="/settings/billing">
            <Button>Upgrade ke Enterprise</Button>
          </Link>
        </div>
      ) : (
        <ErrorBoundary>
          <OnboardingPanel />
        </ErrorBoundary>
      )}
    </div>
  )
}
