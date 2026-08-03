import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api } from '../client'
import { mockApi } from '@/test/server'

afterEach(() => vi.unstubAllGlobals())

describe('API client', () => {
  it('returns parsed JSON on success', async () => {
    mockApi([{ match: /\/projects$/, body: [{ id: 'p1' }] }])
    await expect(api.get('/projects')).resolves.toEqual([{ id: 'p1' }])
  })

  it('returns undefined for 204 rather than failing to parse', async () => {
    mockApi([{ match: /\/projects\/p1$/, method: 'DELETE', status: 204 }])
    await expect(api.delete('/projects/p1')).resolves.toBeUndefined()
  })

  it('turns a FastAPI validation list into a readable sentence', async () => {
    mockApi([
      {
        match: /\/projects$/,
        method: 'POST',
        status: 422,
        body: {
          detail: [
            { loc: ['body', 'name'], msg: 'field required' },
            { loc: ['body', 'objective'], msg: 'too short' },
          ],
        },
      },
    ])

    await expect(api.post('/projects', {})).rejects.toThrow(
      'name: field required; objective: too short',
    )
  })

  it('passes a plain string detail through unchanged', async () => {
    mockApi([
      {
        match: /analyses$/,
        method: 'POST',
        status: 409,
        body: { detail: 'This project has no successfully indexed documents.' },
      },
    ])

    await expect(api.post('/projects/p1/analyses', {})).rejects.toThrow(
      'This project has no successfully indexed documents.',
    )
  })

  it('falls back to a helpful message when the body has no detail', async () => {
    mockApi([{ match: /\/dashboard$/, status: 500, body: {} }])
    await expect(api.get('/dashboard')).rejects.toThrow(/unexpected error/)
  })

  it('flags an unreachable backend distinctly from an HTTP error', async () => {
    mockApi([{ match: /\/dashboard$/, networkError: true }])

    const error = await api.get('/dashboard').catch((caught) => caught)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).isNetwork).toBe(true)
    expect((error as ApiError).message).toMatch(/Could not reach the API/)
  })

  it('classifies not-found and validation errors', async () => {
    mockApi([
      { match: /\/projects\/missing$/, status: 404, body: { detail: 'gone' } },
      { match: /\/projects$/, method: 'POST', status: 400, body: { detail: 'bad' } },
    ])

    const notFound: ApiError = await api
      .get('/projects/missing')
      .then(() => { throw new Error('expected a rejection') }, (e) => e as ApiError)
    expect(notFound.isNotFound).toBe(true)

    const invalid: ApiError = await api
      .post('/projects', {})
      .then(() => { throw new Error('expected a rejection') }, (e) => e as ApiError)
    expect(invalid.isValidation).toBe(true)
  })
})
