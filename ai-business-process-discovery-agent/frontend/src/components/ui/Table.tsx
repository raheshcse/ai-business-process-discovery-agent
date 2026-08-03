import type { ReactNode } from 'react'
import { cn } from '@/lib/cn'

export function Table({
  head,
  children,
  className,
}: {
  head: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="w-full min-w-[40rem] border-collapse text-sm">
        <thead className="table-header">{head}</thead>
        <tbody className="divide-y divide-navy-100">{children}</tbody>
      </table>
    </div>
  )
}

export function Th({
  children,
  className,
}: {
  children?: ReactNode
  className?: string
}) {
  return (
    <th scope="col" className={cn('px-4 py-3 font-semibold', className)}>
      {children}
    </th>
  )
}

export function Td({
  children,
  className,
}: {
  children?: ReactNode
  className?: string
}) {
  return <td className={cn('px-4 py-3 align-middle', className)}>{children}</td>
}
