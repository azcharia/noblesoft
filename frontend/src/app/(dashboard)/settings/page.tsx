/**
 * Settings Page
 * Account and workspace configuration overview.
 */
import Link from 'next/link'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/dashboard/PageHeader'

export default async function SettingsPage() {
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
      email,
      full_name,
      role,
      is_active,
      tenants (
        id,
        company_name,
        subscription_tier,
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
        label="Workspace"
        title="Settings"
        description="Kelola profil pengguna, tenant, dan subscription."
      />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">User Profile</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Full Name</dt>
              <dd className="font-medium text-foreground">{(userData as any)?.full_name || '-'}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Email</dt>
              <dd className="font-medium text-foreground">{(userData as any)?.email || '-'}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Role</dt>
              <dd className="font-medium text-foreground capitalize">{(userData as any)?.role || '-'}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Status</dt>
              <dd>
                <Badge variant={(userData as any)?.is_active ? 'default' : 'destructive'}>
                  {(userData as any)?.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </dd>
            </div>
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Workspace</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="space-y-3 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Company</dt>
              <dd className="font-medium text-foreground">{tenant?.company_name || '-'}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Tenant ID</dt>
              <dd className="font-mono text-xs text-muted-foreground">{tenant?.id || '-'}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Subscription</dt>
              <dd>
                <Badge variant="accent" className="capitalize">
                  {tenant?.subscription_tier || 'unknown'}
                </Badge>
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Max Users</dt>
              <dd className="font-medium text-foreground">{tenant?.max_users ?? '-'}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Workspace Status</dt>
              <dd>
                <Badge variant={tenant?.is_active ? 'default' : 'destructive'}>
                  {tenant?.is_active ? 'Active' : 'Suspended'}
                </Badge>
              </dd>
            </div>
            </dl>

            <div className="mt-5">
              <Link href="/settings/billing">
                <Button variant="outline">Open Billing</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
