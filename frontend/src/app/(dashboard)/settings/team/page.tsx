/**
 * Team Management Settings Page
 * Owner/Admin workspace team lifecycle controls.
 */
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { PageHeader } from '@/components/dashboard/PageHeader'
import { TeamManagementPanel } from '@/components/dashboard/TeamManagementPanel'
import type { TenantUserRole } from '@/lib/api/client'

export default async function TeamManagementPage() {
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
      role
    `
    )
    .eq('id', user.id)
    .single()

  const currentUserId = (userData as any)?.id as string | undefined
  const currentUserRole = (userData as any)?.role as TenantUserRole | undefined

  if (!currentUserId || !currentUserRole) {
    redirect('/settings')
  }

  if (currentUserRole !== 'owner' && currentUserRole !== 'admin') {
    redirect('/settings')
  }

  return (
    <div className="space-y-6">
      <PageHeader
        label="Workspace"
        title="Team Management"
        description="Kelola status anggota tim dan kapasitas seat workspace."
      />

      <TeamManagementPanel currentUserId={currentUserId} currentUserRole={currentUserRole} />
    </div>
  )
}
