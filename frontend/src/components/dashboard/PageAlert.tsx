import { AlertCircle, AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/lib/utils'

const pageAlertVariants = cva('flex items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-sm', {
  variants: {
    variant: {
      error: 'border-destructive/25 bg-destructive/10 text-destructive',
      warning: 'border-amber-300 bg-amber-50 text-amber-700',
      success: 'border-emerald-300 bg-emerald-50 text-emerald-700',
      info: 'border-accent/25 bg-accent/10 text-accent',
    },
  },
  defaultVariants: {
    variant: 'error',
  },
})

interface PageAlertProps extends VariantProps<typeof pageAlertVariants> {
  message: string
  className?: string
}

export function PageAlert({ message, variant, className }: PageAlertProps) {
  const Icon =
    variant === 'warning'
      ? AlertTriangle
      : variant === 'success'
        ? CheckCircle2
        : variant === 'info'
          ? Info
          : AlertCircle

  return (
    <div className={cn(pageAlertVariants({ variant }), className)} role="alert" aria-live="polite">
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <p>{message}</p>
    </div>
  )
}
