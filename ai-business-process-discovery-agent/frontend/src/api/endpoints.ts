/**
 * One function per backend endpoint.
 *
 * Paths and payload shapes are taken from the FastAPI routes in
 * `app/api/routes/`, not guessed. Components never build a URL themselves.
 */

import { api, uploadFile } from './client'
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
} from '@/types/api'

export const healthApi = {
  get: () => api.get<HealthResponse>('/health'),
}

export const dashboardApi = {
  get: () => api.get<DashboardSummary>('/dashboard'),
}

export const projectsApi = {
  list: () => api.get<Project[]>('/projects'),
  get: (projectId: string) => api.get<Project>(`/projects/${projectId}`),
  create: (payload: ProjectCreate) => api.post<Project>('/projects', payload),
  update: (projectId: string, payload: ProjectUpdate) =>
    api.put<Project>(`/projects/${projectId}`, payload),
  remove: (projectId: string) => api.delete(`/projects/${projectId}`),
}

export const documentsApi = {
  listForProject: (projectId: string) =>
    api.get<ProjectDocument[]>(`/projects/${projectId}/documents`),
  get: (documentId: string) => api.get<ProjectDocument>(`/documents/${documentId}`),
  upload: (
    projectId: string,
    file: File,
    onProgress?: (percent: number) => void,
  ) => uploadFile<ProjectDocument>(`/projects/${projectId}/documents`, file, onProgress),
  reindex: (documentId: string) =>
    api.post<ProjectDocument>(`/documents/${documentId}/reindex`),
  remove: (documentId: string) => api.delete(`/documents/${documentId}`),
}

export const analysesApi = {
  listForProject: (projectId: string) =>
    api.get<AnalysisRunSummary[]>(`/projects/${projectId}/analyses`),
  get: (runId: string) => api.get<AnalysisRunDetail>(`/analyses/${runId}`),
  start: (projectId: string, payload: AnalysisRunCreate) =>
    api.post<AnalysisRunDetail>(`/projects/${projectId}/analyses`, payload),
}

export const governanceApi = {
  report: (runId: string) => api.get<GovernanceReport>(`/analyses/${runId}/governance`),
  catalogue: () => api.get<GovernanceCatalogue>('/governance/catalogue'),
}
