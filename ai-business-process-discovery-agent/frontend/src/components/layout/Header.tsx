import { useHealth } from '@/hooks/queries'
import { MenuIcon } from '@/components/ui/icons'
import { Chip } from '@/components/ui/StatusChip'

export function Header({
  title,
  description,
  actions,
  onOpenMenu,
}: {
  title: string
  description?: string
  actions?: React.ReactNode
  onOpenMenu?: () => void
}) {
  const { data: health } = useHealth()

  return (
    <header className="sticky top-0 z-20 border-b border-navy-200/70 bg-white/85 backdrop-blur">
      <div className="flex flex-wrap items-center gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={onOpenMenu}
          className="rounded-lg p-2 text-navy-600 hover:bg-navy-100 lg:hidden"
          aria-label="Open navigation"
        >
          <MenuIcon />
        </button>

        <div className="min-w-0 flex-1">
          <h1 className="truncate text-lg font-semibold tracking-tight text-navy-900">
            {title}
          </h1>
          {description ? (
            <p className="mt-0.5 truncate text-sm text-navy-500">{description}</p>
          ) : null}
        </div>

        <div className="flex items-center gap-3">
          {actions}
          {health ? (
            <Chip tone="success" className="hidden sm:inline-flex">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              {health.llm_provider} · {health.llm_model}
            </Chip>
          ) : (
            <Chip tone="danger" className="hidden sm:inline-flex">
              Backend unreachable
            </Chip>
          )}
        </div>
      </div>
    </header>
  )
}
