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
  ListChecks,
  LifeBuoy,
  Target,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'

interface SidebarProps {
  user: any
  tenant: any
}

interface NavItem {
  name: string
  href: string
  icon: any
  badge?: string
}

const navItems: NavItem[] = [
  {
    name: 'Halaman Utama',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Stok Barang',
    href: '/inventory',
    icon: Package,
  },
  {
    name: 'Nota Penjualan',
    href: '/invoices',
    icon: FileText,
  },
  {
    name: 'Asisten AI',
    href: '/chat',
    icon: MessageSquare,
  },
  {
    name: 'Pengaturan',
    href: '/settings',
    icon: Settings,
  },
]

export function Sidebar({ user, tenant }: SidebarProps) {
  const pathname = usePathname()
  
  return (
    <div className="w-64 bg-white/35 backdrop-blur-lg border-r border-border/50 flex flex-col z-20">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-border/50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-brand-blue to-brand-teal relative overflow-hidden rounded-lg flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <h1 className="text-xl font-display text-brand-teal">
            Noble<span className="text-brand-orange">Soft</span>
          </h1>
        </div>
      </div>
      
      {/* Company info */}
      <div className="px-6 py-4 border-b border-border">
        <p className="text-sm font-semibold text-foreground">{tenant.company_name}</p>
        <div className="flex items-center gap-2 mt-2">
          <Badge variant="accent">
            Open Source
          </Badge>
        </div>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href
          const Icon = item.icon
          
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
