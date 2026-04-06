/**
 * Governance Settings Page
 * Enterprise governance controls: roles, permissions, branches, and audit logs.
 */
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { PageHeader } from '@/components/dashboard/PageHeader'
import { GovernancePanel } from '@/components/dashboard/GovernancePanel'
import { PageAlert } from '@/components/dashboard/PageAlert'
import { Button } from '@/components/ui/button'

export default async function GovernancePage() {
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
        label="Workspace"
        title="Governance"
        description="Kelola custom roles, permission matrix, branch management, dan audit logs."
      />

      {!hasEnterpriseAccess ? (
        <div className="space-y-4">
          <PageAlert
            variant="warning"
            message="Fitur governance memerlukan subscription Enterprise."
          />
          <Link href="/settings/billing">
            <Button>Upgrade ke Enterprise</Button>
          </Link>
        </div>
      ) : (
        <GovernancePanel />
      )}
    </div>
  )
}
