import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

// ── Mocks ──────────────────────────────────────────────────────────────────────

vi.mock('@/lib/api', () => ({
  apiUrl: (p: string) => p,
}))

vi.mock('@/store/ev', () => ({
  useEV: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ addToast: vi.fn() }),
}))

// ── Fetch helpers ──────────────────────────────────────────────────────────────

function makeResponse(data: unknown, ok = true) {
  return Promise.resolve({
    ok,
    status: ok ? 200 : 500,
    json: () => Promise.resolve(data),
  } as Response)
}

const EMPTY_RESPONSE = { events: [], summary: null }

const EVENTS_RESPONSE = {
  events: [
    { id: 'e1', type: 'git.commit', title: 'fix: auth bug', ts: 1700000000, time: '10:00' },
    { id: 'e2', type: 'build.fail',  title: 'CI failed on main', ts: 1700001000, time: '10:30' },
  ],
  summary: { summary: ['Commit + build fail'], commits: 1, builds_failed: 1 },
}

beforeEach(() => {
  vi.clearAllMocks()
  global.fetch = vi.fn(() => makeResponse(EMPTY_RESPONSE)) as typeof fetch
})

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('WorkTimeline', () => {
  it('renders without crash', async () => {
    const { default: WorkTimeline } = await import('@/components/WorkTimeline')
    render(<WorkTimeline />)
    expect(document.body).toBeTruthy()
  })

  it('shows "Čekám na aktivitu…" when events array is empty', async () => {
    global.fetch = vi.fn(() => makeResponse(EMPTY_RESPONSE)) as typeof fetch
    const { default: WorkTimeline } = await import('@/components/WorkTimeline')
    render(<WorkTimeline />)

    await waitFor(() => {
      expect(screen.getByText(/Čekám na aktivitu/i)).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('shows event items when fetch returns events', async () => {
    global.fetch = vi.fn(() => makeResponse(EVENTS_RESPONSE)) as typeof fetch
    const { default: WorkTimeline } = await import('@/components/WorkTimeline')
    render(<WorkTimeline />)

    await waitFor(() => {
      expect(screen.getByText('fix: auth bug')).toBeInTheDocument()
      expect(screen.getByText('CI failed on main')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('shows error state when fetch fails', async () => {
    global.fetch = vi.fn(() => Promise.reject(new Error('Network error'))) as typeof fetch
    const { default: WorkTimeline } = await import('@/components/WorkTimeline')
    render(<WorkTimeline />)

    await waitFor(() => {
      expect(screen.getByText(/backend může být offline/i)).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('refresh button triggers a new fetch', async () => {
    const fetchMock = vi.fn(() => makeResponse(EMPTY_RESPONSE)) as typeof fetch
    global.fetch = fetchMock
    const { default: WorkTimeline } = await import('@/components/WorkTimeline')
    render(<WorkTimeline />)

    // Wait for initial fetch to complete so button is enabled
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1), { timeout: 3000 })

    const refreshBtn = screen.getByTitle('Obnovit')
    await userEvent.click(refreshBtn)

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2), { timeout: 3000 })
  })
})
