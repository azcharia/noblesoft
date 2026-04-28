/**
 * Operations QBR Page
 * Quarterly business review dashboard with goals and hybrid metrics.
 */
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { PageAlert } from '@/components/dashboard/PageAlert'
import { PageHeader } from '@/components/dashboard/PageHeader'
import { QBRPanel } from '@/components/dashboard/QBRPanel'
import { Button } from '@/components/ui/button'

export default async function OperationsQBRPage() {
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
        title="QBR"
        description="Quarterly goals, progress tracking, dan metrics otomatis dari operasional tenant."
      />

      {!hasEnterpriseAccess ? (
        <div className="space-y-4">
          <PageAlert
            variant="warning"
            message="QBR dashboard memerlukan subscription Enterprise."
          />
          <Link href="/settings/billing">
            <Button>Upgrade ke Enterprise</Button>
          </Link>
        </div>
      ) : (
        <ErrorBoundary>
          <QBRPanel />
        </ErrorBoundary>
      )}
    </div>
  )
}
