import type { ReactNode } from 'react'
import { useOutletContext } from 'react-router-dom'
import { Header } from './Header'

interface LayoutContext {
  onOpenMenu: () => void
}

export function PageShell({
  title,
  description,
  actions,
  children,
}: {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
}) {
  const context = useOutletContext<LayoutContext | null>()

  return (
    <>
      <Header
        title={title}
        description={description}
        actions={actions}
        onOpenMenu={context?.onOpenMenu}
      />
      <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl space-y-6">{children}</div>
      </main>
    </>
  )
}
