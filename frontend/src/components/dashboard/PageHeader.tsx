import { type ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface PageHeaderProps {
  title: string
  description?: string
  label?: string
  actions?: ReactNode
  className?: string
}

export function PageHeader({
  title,
  description,
  label = 'Workspace',
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-4 rounded-2xl border border-border/80 bg-card px-5 py-5 shadow-sm sm:flex-row sm:items-center sm:justify-between sm:px-6',
        className
      )}
    >
      <div className="space-y-3">
        <div className="section-label">
          <span className="section-label-dot" aria-hidden="true" />
          <span className="section-label-text">{label}</span>
        </div>
        <div>
          <h1 className="text-3xl leading-tight text-foreground sm:text-4xl">{title}</h1>
          {description ? <p className="mt-2 text-sm text-muted-foreground sm:text-base">{description}</p> : null}
        </div>
      </div>

      {actions ? <div className="flex w-full sm:w-auto sm:justify-end">{actions}</div> : null}
    </div>
  )
}
