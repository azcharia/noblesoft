/**
 * Billing Page
 * Subscription and plan details.
 */
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/dashboard/PageHeader'
import { BillingCheckoutPanel } from '@/components/dashboard/BillingCheckoutPanel'

export default async function BillingPage() {
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
      tenants (
        company_name,
        subscription_tier,
        trial_end_date,
        max_users,
        is_active
      )
    `
    )
    .eq('id', user.id)
    .single()

  const tenant = (userData as any)?.tenants

  return (
    <div className="space-y-6">
      <PageHeader
        label="Subscription"
        title="Billing"
        description="Informasi paket dan status subscription workspace Anda."
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Current Plan</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-xl border border-border bg-muted/60 p-4">
              <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Company</p>
              <p className="mt-1 font-medium text-foreground">{tenant?.company_name || '-'}</p>
            </div>

            <div className="rounded-xl border border-border bg-muted/60 p-4">
              <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Subscription</p>
              <div className="mt-1">
                <Badge variant="accent" className="capitalize">
                  {tenant?.subscription_tier || 'unknown'}
                </Badge>
              </div>
            </div>

            <div className="rounded-xl border border-border bg-muted/60 p-4">
              <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Trial End</p>
              <p className="mt-1 font-medium text-foreground">
                {tenant?.trial_end_date ? new Date(tenant.trial_end_date).toLocaleDateString('id-ID') : '-'}
              </p>
            </div>

            <div className="rounded-xl border border-border bg-muted/60 p-4">
              <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">Max Users</p>
              <p className="mt-1 font-medium text-foreground">{tenant?.max_users ?? '-'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <BillingCheckoutPanel
        currentTier={tenant?.subscription_tier || 'basic'}
        currentCompanyName={tenant?.company_name || 'NobleSoft Tenant'}
      />
    </div>
  )
}
