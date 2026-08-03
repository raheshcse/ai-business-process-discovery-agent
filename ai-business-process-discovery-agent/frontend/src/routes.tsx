import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { DashboardPage } from '@/pages/DashboardPage'
import { ProjectsPage } from '@/pages/ProjectsPage'
import { ProjectWorkspacePage } from '@/pages/ProjectWorkspacePage'
import { AnalysisResultsPage } from '@/pages/AnalysisResultsPage'
import { GovernancePage } from '@/pages/GovernancePage'
import { GovernanceOverviewPage } from '@/pages/GovernanceOverviewPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:projectId" element={<ProjectWorkspacePage />} />
        <Route path="analyses/:runId" element={<AnalysisResultsPage />} />
        <Route path="analyses/:runId/governance" element={<GovernancePage />} />
        <Route path="governance" element={<GovernanceOverviewPage />} />
        <Route path="dashboard" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
