/**
 * React Query bindings.
 *
 * Polling is conditional rather than constant: a document polls only while
 * it is still being indexed, and an analysis polls only while it is still
 * running. Once terminal, the interval stops so an idle tab is quiet.
 */

import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from '@tanstack/react-query'
import { POLL_INTERVAL_MS } from '@/api/config'
import {
  analysesApi,
  dashboardApi,
  documentsApi,
  governanceApi,
  healthApi,
  projectsApi,
} from '@/api/endpoints'
import type {
  AnalysisRunCreate,
  AnalysisRunDetail,
  AnalysisRunSummary,
  DashboardSummary,
  GovernanceCatalogue,
  GovernanceReport,
  HealthResponse,
  Project,
  ProjectCreate,
  ProjectDocument,
  ProjectUpdate,
  WorkflowStatus,
} from '@/types/api'

export const queryKeys = {
  health: ['health'] as const,
  dashboard: ['dashboard'] as const,
  projects: ['projects'] as const,
  project: (id: string) => ['projects', id] as const,
  documents: (projectId: string) => ['projects', projectId, 'documents'] as const,
  analyses: (projectId: string) => ['projects', projectId, 'analyses'] as const,
  analysis: (runId: string) => ['analyses', runId] as const,
  governance: (runId: string) => ['analyses', runId, 'governance'] as const,
  catalogue: ['governance', 'catalogue'] as const,
}

const TERMINAL_STATUSES: WorkflowStatus[] = [
  'completed',
  'failed',
  'insufficient_evidence',
  'governance_blocked',
  'human_review_required',
]

export const isRunInProgress = (status: WorkflowStatus) =>
  !TERMINAL_STATUSES.includes(status)

/* ------------------------------------------------------------------ reads */

export function useHealth(): UseQueryResult<HealthResponse> {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: healthApi.get,
    staleTime: 60_000,
    retry: 1,
  })
}

export function useDashboard(): UseQueryResult<DashboardSummary> {
  return useQuery({ queryKey: queryKeys.dashboard, queryFn: dashboardApi.get })
}

export function useProjects(): UseQueryResult<Project[]> {
  return useQuery({ queryKey: queryKeys.projects, queryFn: projectsApi.list })
}

export function useProject(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.project(projectId ?? ''),
    queryFn: () => projectsApi.get(projectId as string),
    enabled: Boolean(projectId),
  })
}

export function useDocuments(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.documents(projectId ?? ''),
    queryFn: () => documentsApi.listForProject(projectId as string),
    enabled: Boolean(projectId),
    // Keep polling only while something is still being indexed.
    refetchInterval: (query) => {
      const documents = query.state.data as ProjectDocument[] | undefined
      const busy = documents?.some(
        (document) =>
          document.index_status === 'pending' || document.index_status === 'processing',
      )
      return busy ? POLL_INTERVAL_MS : false
    },
  })
}

export function useAnalyses(projectId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.analyses(projectId ?? ''),
    queryFn: () => analysesApi.listForProject(projectId as string),
    enabled: Boolean(projectId),
    refetchInterval: (query) => {
      const runs = query.state.data as AnalysisRunSummary[] | undefined
      return runs?.some((run) => isRunInProgress(run.status)) ? POLL_INTERVAL_MS : false
    },
  })
}

export function useAnalysis(runId: string | undefined) {
  return useQuery({
    queryKey: queryKeys.analysis(runId ?? ''),
    queryFn: () => analysesApi.get(runId as string),
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const run = query.state.data as AnalysisRunDetail | undefined
      return run && isRunInProgress(run.status) ? POLL_INTERVAL_MS : false
    },
  })
}

export function useGovernanceReport(
  runId: string | undefined,
  enabled = true,
): UseQueryResult<GovernanceReport> {
  return useQuery({
    queryKey: queryKeys.governance(runId ?? ''),
    queryFn: () => governanceApi.report(runId as string),
    enabled: Boolean(runId) && enabled,
  })
}

export function useGovernanceCatalogue(): UseQueryResult<GovernanceCatalogue> {
  return useQuery({
    queryKey: queryKeys.catalogue,
    queryFn: governanceApi.catalogue,
    staleTime: Infinity,
  })
}

/* -------------------------------------------------------------- mutations */

export function useCreateProject() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (payload: ProjectCreate) => projectsApi.create(payload),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.projects })
      void client.invalidateQueries({ queryKey: queryKeys.dashboard })
    },
  })
}

export function useUpdateProject() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ProjectUpdate }) =>
      projectsApi.update(id, payload),
    onSuccess: (project) => {
      void client.invalidateQueries({ queryKey: queryKeys.projects })
      void client.invalidateQueries({ queryKey: queryKeys.project(project.id) })
      void client.invalidateQueries({ queryKey: queryKeys.dashboard })
    },
  })
}

export function useDeleteProject() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (projectId: string) => projectsApi.remove(projectId),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.projects })
      void client.invalidateQueries({ queryKey: queryKeys.dashboard })
    },
  })
}

export function useDeleteDocument(projectId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (documentId: string) => documentsApi.remove(documentId),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.documents(projectId) })
      void client.invalidateQueries({ queryKey: queryKeys.dashboard })
    },
  })
}

export function useReindexDocument(projectId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (documentId: string) => documentsApi.reindex(documentId),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.documents(projectId) })
    },
  })
}

export function useStartAnalysis(projectId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (payload: AnalysisRunCreate) => analysesApi.start(projectId, payload),
    onSuccess: (run) => {
      void client.invalidateQueries({ queryKey: queryKeys.analyses(projectId) })
      void client.invalidateQueries({ queryKey: queryKeys.dashboard })
      client.setQueryData(queryKeys.analysis(run.id), run)
    },
  })
}
