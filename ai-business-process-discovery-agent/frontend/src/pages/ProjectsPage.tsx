import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageShell } from '@/components/layout/PageShell'
import { Card, CardBody, CardHeader } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Chip } from '@/components/ui/StatusChip'
import { Modal } from '@/components/ui/Modal'
import { Table, Td, Th } from '@/components/ui/Table'
import {
  Banner,
  EmptyState,
  ErrorState,
  SkeletonRows,
} from '@/components/ui/States'
import {
  ChevronRightIcon,
  EditIcon,
  PlusIcon,
  ProjectsIcon,
  TrashIcon,
} from '@/components/ui/icons'
import { ProjectForm } from '@/features/projects/ProjectForm'
import {
  useCreateProject,
  useDeleteProject,
  useProjects,
  useUpdateProject,
} from '@/hooks/queries'
import { formatRelative, humanise } from '@/lib/format'
import type { Project, ProjectCreate } from '@/types/api'

type Dialog =
  | { kind: 'none' }
  | { kind: 'create' }
  | { kind: 'edit'; project: Project }
  | { kind: 'delete'; project: Project }

export function ProjectsPage() {
  const { data, isLoading, isError, error, refetch } = useProjects()
  const [dialog, setDialog] = useState<Dialog>({ kind: 'none' })
  const [search, setSearch] = useState('')

  const createProject = useCreateProject()
  const updateProject = useUpdateProject()
  const deleteProject = useDeleteProject()

  const close = () => {
    setDialog({ kind: 'none' })
    createProject.reset()
    updateProject.reset()
    deleteProject.reset()
  }

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    if (!term || !data) return data ?? []
    return data.filter((project) =>
      [project.name, project.client_name, project.department, project.industry]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(term)),
    )
  }, [data, search])

  const handleCreate = (values: ProjectCreate) =>
    createProject.mutate(values, { onSuccess: close })

  const handleUpdate = (values: ProjectCreate) => {
    if (dialog.kind !== 'edit') return
    updateProject.mutate({ id: dialog.project.id, payload: values }, { onSuccess: close })
  }

  const handleDelete = () => {
    if (dialog.kind !== 'delete') return
    deleteProject.mutate(dialog.project.id, { onSuccess: close })
  }

  return (
    <PageShell
      title="Projects"
      description="Each project holds its own documents, analyses and audit trail"
      actions={
        <Button
          icon={<PlusIcon className="h-4 w-4" />}
          onClick={() => setDialog({ kind: 'create' })}
        >
          New project
        </Button>
      }
    >
      <Card>
        <CardHeader
          title={`${data?.length ?? 0} project${data?.length === 1 ? '' : 's'}`}
          action={
            data && data.length > 0 ? (
              <input
                className="input h-9 w-full sm:w-64"
                placeholder="Search projects…"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                aria-label="Search projects"
              />
            ) : null
          }
        />
        <CardBody className="p-0 sm:p-0">
          {isLoading ? (
            <div className="p-5 sm:p-6">
              <SkeletonRows rows={4} />
            </div>
          ) : null}

          {isError ? (
            <div className="p-5 sm:p-6">
              <ErrorState error={error} onRetry={() => void refetch()} />
            </div>
          ) : null}

          {data && data.length === 0 ? (
            <div className="p-5 sm:p-6">
              <EmptyState
                icon={<ProjectsIcon className="h-10 w-10" />}
                title="No projects yet"
                description="A project groups the documents for one process area, along with every analysis and governance record produced from them."
                action={
                  <Button
                    icon={<PlusIcon className="h-4 w-4" />}
                    onClick={() => setDialog({ kind: 'create' })}
                  >
                    Create your first project
                  </Button>
                }
              />
            </div>
          ) : null}

          {data && data.length > 0 && filtered.length === 0 ? (
            <div className="p-5 sm:p-6">
              <EmptyState
                title="No matches"
                description={`Nothing matches “${search}”. Try a different search term.`}
                action={
                  <Button variant="secondary" onClick={() => setSearch('')}>
                    Clear search
                  </Button>
                }
              />
            </div>
          ) : null}

          {filtered.length > 0 ? (
            <Table
              head={
                <tr>
                  <Th>Project</Th>
                  <Th className="hidden md:table-cell">Client</Th>
                  <Th className="hidden lg:table-cell">Department</Th>
                  <Th>Status</Th>
                  <Th className="hidden sm:table-cell">Updated</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              }
            >
              {filtered.map((project) => (
                <tr key={project.id} className="hover:bg-navy-50/60">
                  <Td>
                    <Link
                      to={`/projects/${project.id}`}
                      className="group flex items-center gap-2"
                    >
                      <span className="font-medium text-navy-900 group-hover:text-accent-600">
                        {project.name}
                      </span>
                      <ChevronRightIcon className="h-4 w-4 text-navy-300 group-hover:text-accent-500" />
                    </Link>
                    <p className="mt-0.5 line-clamp-1 text-xs text-navy-500">
                      {project.objective}
                    </p>
                  </Td>
                  <Td className="hidden text-navy-600 md:table-cell">
                    {project.client_name ?? '—'}
                  </Td>
                  <Td className="hidden text-navy-600 lg:table-cell">
                    {project.department ?? '—'}
                  </Td>
                  <Td>
                    <Chip tone={project.status === 'active' ? 'info' : 'neutral'}>
                      {humanise(project.status)}
                    </Chip>
                  </Td>
                  <Td className="hidden whitespace-nowrap text-navy-500 sm:table-cell">
                    {formatRelative(project.updated_at)}
                  </Td>
                  <Td>
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label={`Edit ${project.name}`}
                        onClick={() => setDialog({ kind: 'edit', project })}
                      >
                        <EditIcon className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        aria-label={`Delete ${project.name}`}
                        className="text-red-600 hover:bg-red-50"
                        onClick={() => setDialog({ kind: 'delete', project })}
                      >
                        <TrashIcon className="h-4 w-4" />
                      </Button>
                    </div>
                  </Td>
                </tr>
              ))}
            </Table>
          ) : null}
        </CardBody>
      </Card>

      <Modal
        open={dialog.kind === 'create'}
        onClose={close}
        title="New project"
        description="Describe the process area you want to understand."
      >
        {createProject.isError ? (
          <div className="mb-4">
            <Banner tone="danger" title="Could not create the project">
              {(createProject.error as Error).message}
            </Banner>
          </div>
        ) : null}
        <ProjectForm
          formId="create-project"
          submitLabel="Create project"
          submitting={createProject.isPending}
          onSubmit={handleCreate}
          onCancel={close}
        />
      </Modal>

      <Modal
        open={dialog.kind === 'edit'}
        onClose={close}
        title="Edit project"
        description="Changes apply immediately."
      >
        {updateProject.isError ? (
          <div className="mb-4">
            <Banner tone="danger" title="Could not save your changes">
              {(updateProject.error as Error).message}
            </Banner>
          </div>
        ) : null}
        {dialog.kind === 'edit' ? (
          <ProjectForm
            formId="edit-project"
            project={dialog.project}
            submitLabel="Save changes"
            submitting={updateProject.isPending}
            onSubmit={handleUpdate}
            onCancel={close}
          />
        ) : null}
      </Modal>

      <Modal
        open={dialog.kind === 'delete'}
        onClose={close}
        title="Delete this project?"
        footer={
          <>
            <Button variant="secondary" onClick={close}>
              Cancel
            </Button>
            <Button
              variant="danger"
              loading={deleteProject.isPending}
              onClick={handleDelete}
            >
              Delete project
            </Button>
          </>
        }
      >
        {deleteProject.isError ? (
          <div className="mb-4">
            <Banner tone="danger" title="Could not delete the project">
              {(deleteProject.error as Error).message}
            </Banner>
          </div>
        ) : null}
        <p className="text-sm leading-relaxed text-navy-600">
          <strong className="text-navy-900">
            {dialog.kind === 'delete' ? dialog.project.name : ''}
          </strong>{' '}
          will be removed along with its uploaded documents, analyses and
          governance records. This cannot be undone.
        </p>
      </Modal>
    </PageShell>
  )
}
