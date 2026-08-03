import { Link } from 'react-router-dom'
import { PageShell } from '@/components/layout/PageShell'
import { EmptyState } from '@/components/ui/States'

export function NotFoundPage() {
  return (
    <PageShell title="Page not found">
      <EmptyState
        title="That page does not exist"
        description="The link may be out of date, or the item may have been deleted."
        action={
          <Link
            to="/"
            className="inline-flex h-10 items-center rounded-lg bg-accent-500 px-4 text-sm font-medium text-white hover:bg-accent-600"
          >
            Back to dashboard
          </Link>
        }
      />
    </PageShell>
  )
}
