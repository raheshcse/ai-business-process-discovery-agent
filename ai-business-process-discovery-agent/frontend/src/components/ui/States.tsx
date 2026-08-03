/**
 * Loading, empty and error states.
 *
 * These are components rather than inline JSX because every screen needs
 * all three, and inconsistency between them is what makes an app feel
 * unfinished.
 */

import type { ReactNode } from 'react'
import { ApiError } from '@/api/client'
import { cn } from '@/lib/cn'
import { Button } from './Button'
import { Spinner } from './Spinner'

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-16 text-navy-500"
      role="status"
      aria-live="polite"
    >
      <Spinner className="h-6 w-6 text-accent-500" />
      <p className="text-sm">{label}</p>
    </div>
  )
}

export function SkeletonRows({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3" aria-hidden="true">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="skeleton h-14 w-full" />
      ))}
    </div>
  )
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string
  description: string
  action?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-navy-200 bg-navy-50/40 px-6 py-14 text-center">
      {icon ? <div className="text-navy-300">{icon}</div> : null}
      <h3 className="text-base font-semibold text-navy-900">{title}</h3>
      <p className="max-w-md text-sm leading-relaxed text-navy-500">{description}</p>
      {action ? <div className="pt-1">{action}</div> : null}
    </div>
  )
}

function describe(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return 'Something went wrong.'
}

export function ErrorState({
  error,
  onRetry,
  title = 'We could not load this',
}: {
  error: unknown
  onRetry?: () => void
  title?: string
}) {
  const isNetwork = error instanceof ApiError && error.isNetwork
  return (
    <div
      className="rounded-xl border border-red-200 bg-red-50/70 px-6 py-8 text-center"
      role="alert"
    >
      <h3 className="text-base font-semibold text-red-900">
        {isNetwork ? 'Cannot reach the server' : title}
      </h3>
      <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-red-800">
        {describe(error)}
      </p>
      {onRetry ? (
        <div className="mt-4">
          <Button variant="secondary" size="sm" onClick={onRetry}>
            Try again
          </Button>
        </div>
      ) : null}
    </div>
  )
}

export function InlineError({ children }: { children: ReactNode }) {
  return (
    <p className="mt-1.5 text-xs font-medium text-red-700" role="alert">
      {children}
    </p>
  )
}

export function Banner({
  tone = 'info',
  title,
  children,
  action,
}: {
  tone?: 'info' | 'warning' | 'danger' | 'success'
  title: string
  children?: ReactNode
  action?: ReactNode
}) {
  const tones = {
    info: 'border-accent-500/25 bg-accent-500/5 text-navy-800',
    warning: 'border-amber-300 bg-amber-50 text-amber-900',
    danger: 'border-red-300 bg-red-50 text-red-900',
    success: 'border-emerald-300 bg-emerald-50 text-emerald-900',
  }
  return (
    <div className={cn('rounded-xl border px-4 py-3.5', tones[tone])}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold">{title}</p>
          {children ? (
            <div className="mt-1 text-sm leading-relaxed opacity-90">{children}</div>
          ) : null}
        </div>
        {action}
      </div>
    </div>
  )
}
