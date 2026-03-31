import { type ReactNode } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

const statValueVariants = cva('text-2xl font-semibold tracking-tight sm:text-3xl', {
  variants: {
    tone: {
      default: 'text-foreground',
      accent: 'gradient-text',
      warning: 'text-amber-600',
      danger: 'text-destructive',
      success: 'text-emerald-700',
    },
  },
  defaultVariants: {
    tone: 'default',
  },
})

interface StatCardProps extends VariantProps<typeof statValueVariants> {
  title: string
  value: ReactNode
  subtitle?: string
  className?: string
}

export function StatCard({ title, value, subtitle, tone, className }: StatCardProps) {
  return (
    <Card className={cn('h-full', className)}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className={cn(statValueVariants({ tone }))}>{value}</p>
        {subtitle ? <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p> : null}
      </CardContent>
    </Card>
  )
}
