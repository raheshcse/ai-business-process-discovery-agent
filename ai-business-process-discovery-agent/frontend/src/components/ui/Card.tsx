import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export function Card({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={cn('card', className)}>{children}</section>
}

export function CardHeader({
  title,
  description,
  action,
  className,
}: {
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-wrap items-start justify-between gap-3 border-b border-navy-100 px-5 py-4 sm:px-6',
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className="text-sm font-semibold tracking-tight text-navy-900">{title}</h2>
        {description ? (
          <p className="mt-1 text-sm text-navy-500">{description}</p>
        ) : null}
      </div>
      {action}
    </div>
  )
}

export function CardBody({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={cn('px-5 py-5 sm:px-6', className)}>{children}</div>
}

export function StatCard({
  label,
  value,
  hint,
  tone = 'default',
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  tone?: 'default' | 'warning' | 'danger' | 'success'
}) {
  const accents = {
    default: 'text-navy-900',
    warning: 'text-amber-700',
    danger: 'text-red-700',
    success: 'text-emerald-700',
  }
  return (
    <div className="card p-5">
      <p className="text-xs font-medium uppercase tracking-wide text-navy-500">
        {label}
      </p>
      <p className={cn('mt-2 text-3xl font-semibold tabular-nums', accents[tone])}>
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-navy-500">{hint}</p> : null}
    </div>
  )
}
