import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/cn'
import {
  DashboardIcon,
  ProjectsIcon,
  ShieldIcon,
} from '@/components/ui/icons'

const LINKS = [
  { to: '/', label: 'Dashboard', icon: DashboardIcon, end: true },
  { to: '/projects', label: 'Projects', icon: ProjectsIcon, end: false },
  { to: '/governance', label: 'Governance', icon: ShieldIcon, end: false },
]

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col bg-hero-gradient">
      <div className="flex items-center gap-3 px-5 py-6">
        <div className="grid h-9 w-9 place-items-center rounded-lg bg-accent-500/15 ring-1 ring-inset ring-accent-400/30">
          <ShieldIcon className="h-5 w-5 text-accent-400" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">Process Discovery</p>
          <p className="truncate text-xs text-navy-300">Governed AI analysis</p>
        </div>
      </div>

      <nav aria-label="Primary" className="flex-1 space-y-1 px-3">
        {LINKS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-white/10 text-white'
                  : 'text-navy-300 hover:bg-white/5 hover:text-white',
              )
            }
          >
            <Icon className="h-5 w-5 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 pb-6 pt-4">
        <p className="text-xs leading-relaxed text-navy-400">
          Every analysis passes through X-Verba governance gates and is
          recorded in a tamper-evident audit ledger.
        </p>
      </div>
    </div>
  )
}
