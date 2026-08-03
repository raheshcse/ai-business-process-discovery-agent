import { Spinner } from '@/components/ui/Spinner'
import { cn } from '@/lib/cn'
import type { WorkflowStage, WorkflowStatus } from '@/types/api'

/** The five analysis stages, in the order `build_process_discovery_graph`
 *  wires them. Governance invariants run between each. */
const STAGES: { stage: WorkflowStage; label: string }[] = [
  { stage: 'retrieval', label: 'Finding evidence' },
  { stage: 'process_discovery', label: 'Discovering the process' },
  { stage: 'bottleneck_analysis', label: 'Analysing bottlenecks' },
  { stage: 'risk_analysis', label: 'Analysing risks' },
  { stage: 'automation_analysis', label: 'Finding automation' },
  { stage: 'final_synthesis', label: 'Writing the summary' },
]

export function RunProgress({
  status,
  currentStage,
}: {
  status: WorkflowStatus
  currentStage: WorkflowStage
}) {
  const activeIndex = STAGES.findIndex((item) => item.stage === currentStage)
  const isFinished = status === 'completed'

  return (
    <ol className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {STAGES.map((item, index) => {
        const done = isFinished || (activeIndex > -1 && index < activeIndex)
        const active = !isFinished && index === activeIndex
        return (
          <li
            key={item.stage}
            className={cn(
              'rounded-lg border px-3 py-2.5 text-xs transition-colors',
              done
                ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                : active
                  ? 'border-accent-400 bg-accent-500/10 text-accent-700'
                  : 'border-navy-200 bg-white text-navy-400',
            )}
          >
            <div className="flex items-center gap-1.5">
              {active ? <Spinner className="h-3 w-3" /> : null}
              {done ? <span aria-hidden="true">✓</span> : null}
              <span className="font-medium">{item.label}</span>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
