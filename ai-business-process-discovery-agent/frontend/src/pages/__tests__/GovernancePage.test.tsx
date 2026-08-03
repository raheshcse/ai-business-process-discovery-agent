import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GovernancePage } from '../GovernancePage'
import { renderPage } from '@/test/utils'
import { mockApi } from '@/test/server'
import { governanceReport, health } from '@/test/fixtures'

afterEach(() => vi.unstubAllGlobals())

const render = () =>
  renderPage(<GovernancePage />, {
    route: '/analyses/run-1/governance',
    path: '/analyses/:runId/governance',
  })

describe('Governance and audit', () => {
  it('states the verdict in business language', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /governance$/, body: governanceReport },
    ])

    render()

    expect(
      await screen.findByText('This analysis passed every governance check'),
    ).toBeInTheDocument()
  })

  it('explains each gate in terms of what it protected against', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /governance$/, body: governanceReport },
    ])

    render()

    expect(
      await screen.findByText(
        /Checked there was relevant evidence from this project/,
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Confirmed every process finding cited a real source/),
    ).toBeInTheDocument()
  })

  it('hides jargon until the reader asks for it', async () => {
    const user = userEvent.setup()
    mockApi([
      { match: /\/health$/, body: health },
      { match: /governance$/, body: governanceReport },
    ])

    render()

    await screen.findByText('This analysis passed every governance check')
    expect(screen.queryByText(/process_discovery_pre_node/)).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Show technical detail/ }))
    expect(await screen.findByText(/process_discovery_pre_node/)).toBeInTheDocument()
    // The raw hash-chained ledger appears only in technical mode.
    expect(screen.getByText('Audit ledger')).toBeInTheDocument()
    expect(screen.getByText('MONITOR')).toBeInTheDocument()
  })

  it('reports a failing audit check honestly rather than as a pass', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /governance$/, body: governanceReport },
    ])

    render()

    expect(await screen.findByText('1 of 5 checks are not met')).toBeInTheDocument()
    expect(
      screen.getByText(/no human approval or re-enablement workflow/),
    ).toBeInTheDocument()
    expect(screen.getByText('1 record affected')).toBeInTheDocument()
  })

  it('shows tamper evidence and its limits', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      { match: /governance$/, body: governanceReport },
    ])

    render()

    expect(await screen.findByText('Unaltered')).toBeInTheDocument()
    expect(
      screen.getByText(/does not guarantee no Inadmissible State/),
    ).toBeInTheDocument()
  })

  it('reports a blocked run with the reason it stopped', async () => {
    mockApi([
      { match: /\/health$/, body: health },
      {
        match: /governance$/,
        body: {
          ...governanceReport,
          governance_status: 'blocked',
          terminal_state_name: 'UNSUPPORTED_FINDINGS',
          denial_summary: {
            construct_name: 'risk_scope_invariant',
            safe_reason: 'Governance denied automated execution at risk_scope_invariant.',
            human_review_required: false,
          },
          decisions: [
            {
              ...governanceReport.decisions[1],
              outcome: 'denied',
              construct_name: 'risk_scope_invariant',
              terminal_state_name: 'UNSUPPORTED_FINDINGS',
            },
          ],
        },
      },
    ])

    render()

    expect(
      await screen.findByText('This analysis was stopped by a governance check'),
    ).toBeInTheDocument()
    expect(screen.getByText('Why it stopped')).toBeInTheDocument()
    expect(screen.getAllByText('Blocked').length).toBeGreaterThan(0)
  })
})
