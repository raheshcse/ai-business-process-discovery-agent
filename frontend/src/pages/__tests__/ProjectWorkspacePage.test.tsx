import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { ProjectWorkspacePage } from '../ProjectWorkspacePage'
import { renderPage } from '@/test/utils'
import { mockApi } from '@/test/server'
import {
  completedRun,
  failedDocument,
  health,
  indexedDocument,
  project,
} from '@/test/fixtures'

afterEach(() => vi.unstubAllGlobals())

const render = () =>
  renderPage(<ProjectWorkspacePage />, {
    route: '/projects/project-1',
    path: '/projects/:projectId',
  })

describe('Project workspace', () => {
  it('shows the project summary and evidence readiness', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/projects\/project-1$/, body: project },
      { match: /documents$/, body: [indexedDocument, failedDocument] },
      { match: /analyses$/, body: [] },
    ])

    render()

    expect(await screen.findByText('Project summary')).toBeInTheDocument()
    expect(screen.getByText('Northwind Ltd')).toBeInTheDocument()
    expect(screen.getByText('1 of 2 ready')).toBeInTheDocument()
  })

  it('shows indexing status per document, with the reason for a failure', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/projects\/project-1$/, body: project },
      { match: /documents$/, body: [indexedDocument, failedDocument] },
      { match: /analyses$/, body: [] },
    ])

    render()

    expect(await screen.findByText('Ready')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
    expect(
      screen.getByText('Text could not be extracted. The file may be scanned.'),
    ).toBeInTheDocument()
    expect(screen.getByText(/12 searchable sections/)).toBeInTheDocument()
    // A failed document can be retried.
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
  })

  it('will not offer an analysis until something is indexed', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/projects\/project-1$/, body: project },
      { match: /documents$/, body: [failedDocument] },
      { match: /analyses$/, body: [] },
    ])

    render()

    expect(await screen.findByText('No usable evidence yet')).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /Run governed analysis/ }),
    ).not.toBeInTheDocument()
  })

  it('says it is preparing while indexing is still running', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/projects\/project-1$/, body: project },
      {
        match: /documents$/,
        body: [{ ...indexedDocument, index_status: 'processing' }],
      },
      { match: /analyses$/, body: [] },
    ])

    render()

    expect(await screen.findByText('Preparing your documents')).toBeInTheDocument()
  })

  it('offers the analysis form once evidence is ready', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/projects\/project-1$/, body: project },
      { match: /documents$/, body: [indexedDocument] },
      { match: /analyses$/, body: [] },
    ])

    render()

    expect(
      await screen.findByRole('button', { name: /Run governed analysis/ }),
    ).toBeEnabled()
    expect(screen.getByLabelText(/What do you want to understand/)).toBeInTheDocument()
  })

  it('lists previous analyses and links to each', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/projects\/project-1$/, body: project },
      { match: /documents$/, body: [indexedDocument] },
      { match: /analyses$/, body: [completedRun] },
    ])

    render()

    const link = await screen.findByRole('link', {
      name: /How does the invoice approval process work end to end/,
    })
    expect(link).toHaveAttribute('href', '/analyses/run-1')
  })

  it('prompts for documents when the project is empty', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/projects\/project-1$/, body: project },
      { match: /documents$/, body: [] },
      { match: /analyses$/, body: [] },
    ])

    render()

    expect(await screen.findByText('No documents yet')).toBeInTheDocument()
    expect(screen.getByText('Drop process documentation here')).toBeInTheDocument()
  })

  it('explains a missing project rather than rendering a blank page', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      {
        match: /\/projects\/project-1$/,
        status: 404,
        body: { detail: 'Project with id project-1 not found' },
      },
    ])

    render()

    expect(
      await screen.findByText('We could not open this project'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Project with id project-1 not found'),
    ).toBeInTheDocument()
  })
})
