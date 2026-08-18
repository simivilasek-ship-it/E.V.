import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import React from 'react'

// ── Mocks ──────────────────────────────────────────────────────────────────────

vi.mock('@/lib/api', () => ({
  apiUrl: (p: string) => p,
}))

const baseState = {
  system: { cpu: 42.5, ram: 61.0, disk: 30.2, load: 1.5 },
  agents: [],
  addToast: vi.fn(),
}

vi.mock('@/store/ev', () => ({
  useEV: (selector: (s: typeof baseState) => unknown) => selector(baseState),
}))

// ── Fetch helpers ──────────────────────────────────────────────────────────────

function makeResponse(data: unknown, ok = true) {
  return Promise.resolve({
    ok,
    status: ok ? 200 : 500,
    json: () => Promise.resolve(data),
  } as Response)
}

const JOBS_RESPONSE = [
  { name: 'health_check', next_run: '2024-01-01T10:00:00', runs: 5, errors: 0 },
]
const AUDIT_RESPONSE = [
  { ts: '2024-01-01T09:00:00', action: 'login', approved: true },
]

beforeEach(() => {
  vi.clearAllMocks()
  global.fetch = vi.fn((url: string) => {
    if (String(url).includes('/api/scheduler/jobs')) return makeResponse(JOBS_RESPONSE)
    if (String(url).includes('/api/audit'))          return makeResponse(AUDIT_RESPONSE)
    return makeResponse({})
  }) as typeof fetch
})

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('DashboardPanel', () => {
  it('renders without crash', async () => {
    const { default: DashboardPanel } = await import('@/components/DashboardPanel')
    render(<DashboardPanel />)
    expect(document.body).toBeTruthy()
  })

  it('shows loading skeleton initially', async () => {
    // Delay fetch so loading state is visible during render
    global.fetch = vi.fn(() => new Promise(() => {})) as typeof fetch
    const { default: DashboardPanel } = await import('@/components/DashboardPanel')
    const { container } = render(<DashboardPanel />)
    expect(container.querySelector('.skeleton')).toBeInTheDocument()
  })

  it('shows CPU and RAM values from store after fetch resolves', async () => {
    const { default: DashboardPanel } = await import('@/components/DashboardPanel')
    render(<DashboardPanel />)

    // CPU and RAM values come from the zustand store (system), shown in StatCard
    await waitFor(() => {
      expect(screen.getByText('42.5')).toBeInTheDocument()
      expect(screen.getByText('61.0')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('shows empty state gracefully when backend is unreachable', async () => {
    // DashboardPanel uses Promise.allSettled — fetch rejections degrade gracefully
    // to empty jobs/audit rather than showing an error banner.
    global.fetch = vi.fn(() => Promise.reject(new Error('fetch failed'))) as typeof fetch
    const { default: DashboardPanel } = await import('@/components/DashboardPanel')
    render(<DashboardPanel />)

    await waitFor(() => {
      expect(screen.getByText('No scheduled jobs')).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})
