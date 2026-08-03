import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ProjectsPage } from '../ProjectsPage'
import { renderPage } from '@/test/utils'
import { mockApi } from '@/test/server'
import { health, project } from '@/test/fixtures'

afterEach(() => vi.unstubAllGlobals())

describe('Projects', () => {
  it('lists projects and links each to its workspace', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/projects$/, body: [project] },
    ])

    renderPage(<ProjectsPage />, { route: '/projects', path: '/projects' })

    const link = await screen.findByRole('link', { name: /Accounts Payable Review/ })
    expect(link).toHaveAttribute('href', '/projects/project-1')
    expect(screen.getByText('Northwind Ltd')).toBeInTheDocument()
  })

  it('offers a starting point when there are no projects', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/projects$/, body: [] },
    ])

    renderPage(<ProjectsPage />, { route: '/projects', path: '/projects' })

    expect(await screen.findByText('No projects yet')).toBeInTheDocument()
  })

  it('blocks submission until the required fields are filled', async () => {
    const user = userEvent.setup()
    const { calls } = mockApi([
      { match: /\/health$/, body: health },
      { match: /\/projects$/, body: [] },
      { match: /\/projects$/, method: 'POST', status: 201, body: project },
    ])

    renderPage(<ProjectsPage />, { route: '/projects', path: '/projects' })

    await user.click(await screen.findByRole('button', { name: /New project/ }))
    await user.click(screen.getByRole('button', { name: 'Create project' }))

    expect(await screen.findByText('Give the project a name.')).toBeInTheDocument()
    expect(
      screen.getByText('Describe what you want to discover.'),
    ).toBeInTheDocument()
    expect(calls.some((call) => call.method === 'POST')).toBe(false)
  })

  it('sends a valid project to the API with blanks as null', async () => {
    const user = userEvent.setup()
    const { calls } = mockApi([
      { match: /\/health$/, body: health },
      { match: /\/projects$/, body: [] },
      { match: /\/projects$/, method: 'POST', status: 201, body: project },
    ])

    renderPage(<ProjectsPage />, { route: '/projects', path: '/projects' })

    await user.click(await screen.findByRole('button', { name: /New project/ }))
    await user.type(screen.getByLabelText(/Project name/), 'Order to cash')
    await user.type(
      screen.getByLabelText(/Objective/),
      'Map how orders become cash today.',
    )
    await user.click(screen.getByRole('button', { name: 'Create project' }))

    await waitFor(() => {
      const post = calls.find((call) => call.method === 'POST')
      expect(post?.body).toEqual({
        name: 'Order to cash',
        objective: 'Map how orders become cash today.',
        client_name: null,
        department: null,
        industry: null,
        status: 'draft',
      })
    })
  })

  it('surfaces an API rejection inside the dialog', async () => {
    const user = userEvent.setup()
    mockApi([
      { match: /\/health$/, body: health },
      { match: /\/projects$/, body: [] },
      {
        match: /\/projects$/,
        method: 'POST',
        status: 422,
        body: { detail: [{ loc: ['body', 'name'], msg: 'too long' }] },
      },
    ])

    renderPage(<ProjectsPage />, { route: '/projects', path: '/projects' })

    await user.click(await screen.findByRole('button', { name: /New project/ }))
    await user.type(screen.getByLabelText(/Project name/), 'Order to cash')
    await user.type(screen.getByLabelText(/Objective/), 'Map order to cash.')
    await user.click(screen.getByRole('button', { name: 'Create project' }))

    expect(await screen.findByText('Could not create the project')).toBeInTheDocument()
    expect(screen.getByText('name: too long')).toBeInTheDocument()
  })
})
