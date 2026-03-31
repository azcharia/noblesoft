/**
 * Dashboard Header
 * Minimalist modern design
 */
'use client'

import { Bell, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { signOut } from '@/lib/supabase/client'

interface HeaderProps {
  user: any
  companyName: string
  subscriptionTier: string
}

export function Header({ user, companyName, subscriptionTier }: HeaderProps) {
  const handleSignOut = async () => {
    await signOut()
  }
  
  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card px-4 sm:px-6">
      <div className="min-w-0">
        <h2 className="truncate text-lg font-semibold text-foreground">
          Welcome back, {user.full_name || 'User'}
        </h2>
        <div className="mt-1 flex items-center gap-2">
          <p className="truncate text-sm text-muted-foreground">{companyName}</p>
          <Badge variant="accent" className="hidden capitalize sm:inline-flex">
            {subscriptionTier}
          </Badge>
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" className="rounded-lg">
          <Bell className="w-5 h-5" />
        </Button>
        
        <Button
          variant="ghost"
          size="sm"
          onClick={handleSignOut}
          className="gap-2 rounded-lg"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </Button>
      </div>
    </header>
  )
}
