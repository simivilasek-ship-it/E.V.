import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import React from 'react'

// ── Mocks ──────────────────────────────────────────────────────────────────────

vi.mock('@/lib/api', () => ({
  apiUrl: (path: string) => `http://localhost:8002${path}`,
}))

vi.mock('@/lib/audioDuplex', () => ({
  AudioDuplex: vi.fn().mockImplementation(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    send: vi.fn(),
  })),
}))

const mockAddToast = vi.fn()

vi.mock('@/store/ev', () => ({
  useEV: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ addToast: mockAddToast }),
}))

// ── Fetch mock helpers ─────────────────────────────────────────────────────────

const HEALTH_RESPONSE = {
  score: 85,
  checks_ok: 5,
  checks_total: 6,
  checks: {
    backend: { ok: true, hint: '' },
    ollama: { ok: true, hint: '' },
    database: { ok: true, hint: '' },
    audio: { ok: false, hint: 'portaudio not found' },
    tts: { ok: true, hint: '' },
    stt: { ok: true, hint: '' },
  },
  fixes: [],
  mcp: { score: 100, enabled_total: 2, ready_total: 2 },
}

const SETTINGS_RESPONSE = {
  model: 'llama3',
  history_size: 20,
  tts_enabled: false,
  tts_voice: '',
  tts_rate: 150,
  tts_streaming: false,
  stt_language: 'cs-CZ',
  stt_energy_threshold: 300,
  stt_timeout: 10,
  wake_word_enabled: false,
  wake_word: 'jarvis',
  agent_max_steps: 7,
  agent_timeout: 60,
}

function makeFetchResponse(data: unknown, ok = true) {
  return Promise.resolve({
    ok,
    status: ok ? 200 : 500,
    json: () => Promise.resolve(data),
  } as Response)
}

beforeEach(() => {
  vi.clearAllMocks()
  global.fetch = vi.fn((url: string) => {
    if (url.includes('/api/settings')) return makeFetchResponse(SETTINGS_RESPONSE)
    if (url.includes('/api/models')) return makeFetchResponse(['llama3', 'mistral'])
    if (url.includes('/api/tts/voices')) return makeFetchResponse(['cs-CZ-ZuzanaNeural', 'en-US-AriaNeural'])
    if (url.includes('/api/mcp/status')) return makeFetchResponse({ servers: [] })
    if (url.includes('/api/health/check')) return makeFetchResponse(HEALTH_RESPONSE)
    if (url.includes('/api/health')) return makeFetchResponse({ status: 'ok' })
    return makeFetchResponse({}, false)
  }) as typeof fetch
})

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('SettingsPanel', () => {
  it('renders without crashing', async () => {
    const { default: SettingsPanel } = await import('@/components/SettingsPanel')
    render(<SettingsPanel />)
    // Loading state or content — either way the component mounts
    expect(document.body).toBeTruthy()
  })

  it('displays the health score after loading', async () => {
    const { default: SettingsPanel } = await import('@/components/SettingsPanel')
    render(<SettingsPanel />)

    // Wait for the async fetch to resolve and the score to appear
    await waitFor(() => {
      expect(screen.getByText('85%')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('displays Ready Score label', async () => {
    const { default: SettingsPanel } = await import('@/components/SettingsPanel')
    render(<SettingsPanel />)

    await waitFor(() => {
      expect(screen.getByText('Ready Score')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('displays checks ok/total from health data', async () => {
    const { default: SettingsPanel } = await import('@/components/SettingsPanel')
    render(<SettingsPanel />)

    await waitFor(() => {
      const text = screen.getByText(/Checks:\s*5\/6/)
      expect(text).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('calls the health check API endpoint', async () => {
    const { default: SettingsPanel } = await import('@/components/SettingsPanel')
    render(<SettingsPanel />)

    await waitFor(() => {
      const urls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls.map(
        ([url]: [string]) => url
      )
      expect(urls.some((u: string) => u.includes('/api/health/check'))).toBe(true)
    }, { timeout: 3000 })
  })
})
