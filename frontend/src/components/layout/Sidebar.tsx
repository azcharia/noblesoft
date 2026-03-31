/**
 * Sidebar Navigation
 * Minimalist modern design with gradient accents
 */
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  Package,
  FileText,
  MessageSquare,
  Settings,
  BarChart3,
  Lock,
  Sparkles,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'

interface SidebarProps {
  user: any
  tenant: any
  subscriptionTier: 'trial' | 'basic' | 'pro' | 'enterprise'
}

interface NavItem {
  name: string
  href: string
  icon: any
  requiredTier?: ('trial' | 'basic' | 'pro' | 'enterprise')[]
  badge?: string
}

const navItems: NavItem[] = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Inventory',
    href: '/inventory',
    icon: Package,
  },
  {
    name: 'Invoices',
    href: '/invoices',
    icon: FileText,
  },
  {
    name: 'AI Assistant',
    href: '/chat',
    icon: MessageSquare,
    requiredTier: ['pro', 'enterprise'],
    badge: 'Pro',
  },
  {
    name: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
    requiredTier: ['pro', 'enterprise'],
    badge: 'Pro',
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
  },
]

export function Sidebar({ user, tenant, subscriptionTier }: SidebarProps) {
  const pathname = usePathname()
  
  const hasAccess = (item: NavItem) => {
    if (!item.requiredTier) return true
    return item.requiredTier.includes(subscriptionTier)
  }
  
  return (
    <div className="w-64 bg-card border-r border-border flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-accent to-accent-secondary rounded-lg flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <h1 className="text-xl font-display">
            Noble<span className="gradient-text">Soft</span>
          </h1>
        </div>
      </div>
      
      {/* Company info */}
      <div className="px-6 py-4 border-b border-border">
        <p className="text-sm font-semibold text-foreground">{tenant.company_name}</p>
        <div className="flex items-center gap-2 mt-2">
          <Badge 
            variant={subscriptionTier === 'pro' || subscriptionTier === 'enterprise' ? 'accent' : 'secondary'}
            className="capitalize"
          >
            {subscriptionTier.charAt(0).toUpperCase() + subscriptionTier.slice(1)}
          </Badge>
        </div>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href
          const canAccess = hasAccess(item)
          const Icon = item.icon
          
          if (!canAccess) {
            return (
              <div
                key={item.name}
                className={cn(
                  'flex items-center justify-between px-3 py-2.5 rounded-lg',
                  'text-muted-foreground cursor-not-allowed opacity-50'
                )}
                title={`Upgrade to ${item.badge} to access this feature`}
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5" />
                  <span className="text-sm font-medium">{item.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  {item.badge && (
                    <span className="text-xs font-mono text-accent">{item.badge}</span>
                  )}
                  <Lock className="w-4 h-4" />
                </div>
              </div>
            )
          }
          
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                'flex items-center justify-between px-3 py-2.5 rounded-lg transition-all duration-200',
                isActive
                  ? 'bg-accent/10 text-accent font-medium shadow-sm'
                  : 'text-foreground hover:bg-muted'
              )}
            >
              <div className="flex items-center gap-3">
                <Icon className="w-5 h-5" />
                <span className="text-sm font-medium">{item.name}</span>
              </div>
              {item.badge && !isActive && (
                <span className="text-xs font-mono text-accent">{item.badge}</span>
              )}
            </Link>
          )
        })}
      </nav>
      
      {/* Upgrade CTA */}
      {subscriptionTier !== 'pro' && subscriptionTier !== 'enterprise' && (
        <div className="p-4 m-3 bg-gradient-to-br from-accent/5 to-accent-secondary/5 rounded-xl border border-accent/20">
          <div className="flex items-start gap-2 mb-2">
            <div className="w-2 h-2 rounded-full bg-accent mt-1.5 animate-pulse-slow" />
            <div>
              <p className="text-sm font-semibold text-foreground">
                Upgrade to Pro
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Unlock AI Assistant & Analytics
              </p>
            </div>
          </div>
          <Link
            href="/settings/billing"
            className="block w-full px-3 py-2 text-xs font-medium text-center text-white gradient-bg rounded-lg hover:shadow-accent transition-all duration-200 hover:-translate-y-0.5"
          >
            Upgrade Now
          </Link>
        </div>
      )}
      
      {/* User info */}
      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl gradient-bg flex items-center justify-center text-white text-sm font-semibold shadow-accent">
            {user.full_name?.charAt(0) || user.email?.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-foreground truncate">
              {user.full_name || 'User'}
            </p>
            <p className="text-xs text-muted-foreground truncate">{user.email}</p>
          </div>
        </div>
      </div>
    </div>
  )
}
