/**
 * Dashboard Header
 * Minimalist modern design
 */
'use client'

import { usePathname } from 'next/navigation'
import { Bell, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { signOut } from '@/lib/supabase/client'

interface HeaderProps {
  user: any
  companyName: string
}

export function Header({ user, companyName }: HeaderProps) {
  const pathname = usePathname()
  const handleSignOut = async () => {
    await signOut()
  }
  
  return (
    <header key={pathname} className="flex h-16 items-center justify-between border-b border-border/50 bg-white/35 backdrop-blur-lg px-4 sm:px-6 z-20 transition-all duration-300">
      <div className="min-w-0">
        <h2 className="truncate text-lg font-semibold text-foreground">
          Welcome back, {user.full_name || 'User'}
        </h2>
        <div className="mt-1 flex items-center gap-2">
          <p className="truncate text-sm text-muted-foreground">{companyName}</p>
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
