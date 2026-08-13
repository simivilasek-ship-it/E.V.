import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

// ── Mocks ──────────────────────────────────────────────────────────────────────

vi.mock('@/lib/api', () => ({
  apiUrl: (p: string) => p,
}))

const mockAddToast = vi.fn()

vi.mock('@/store/ev', () => ({
  useEV: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ addToast: mockAddToast }),
}))

// ── Fetch helpers ──────────────────────────────────────────────────────────────

function makeResponse(data: unknown, ok = true) {
  return Promise.resolve({
    ok,
    status: ok ? 200 : 500,
    json: () => Promise.resolve(data),
  } as Response)
}

const VOICE_HEALTH = {
  voice: {
    stt: { engine: 'vosk', language: 'cs-CZ', available: true },
    tts: { engine: 'edge-tts', voice: 'cs-CZ-ZuzanaNeural', rate: 150, available: true },
    wake_word: { enabled: false, available: true },
    duplex: { enabled: false },
  },
}

beforeEach(() => {
  vi.clearAllMocks()
  global.fetch = vi.fn(() => makeResponse(VOICE_HEALTH)) as typeof fetch
  // Ensure SpeechRecognition is available by default
  ;(window as any).SpeechRecognition = vi.fn()
  delete (window as any).webkitSpeechRecognition
})

afterEach(() => {
  delete (window as any).SpeechRecognition
  delete (window as any).webkitSpeechRecognition
})

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('VoicePanel', () => {
  it('renders without crash', async () => {
    const { default: VoicePanel } = await import('@/components/VoicePanel')
    render(<VoicePanel />)
    expect(document.body).toBeTruthy()
  })

  it('shows "Nedostupné — použij Chrome" when SpeechRecognition is not in window', async () => {
    delete (window as any).SpeechRecognition
    delete (window as any).webkitSpeechRecognition

    const { default: VoicePanel } = await import('@/components/VoicePanel')
    render(<VoicePanel />)

    await waitFor(() => {
      expect(screen.getByText('Nedostupné — použij Chrome')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('shows duplex toggle', async () => {
    const { default: VoicePanel } = await import('@/components/VoicePanel')
    render(<VoicePanel />)

    await waitFor(() => {
      expect(screen.getByText('Duplex stream')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('toggle calls PATCH /api/settings', async () => {
    const fetchMock = vi.fn((url: string) => {
      if (String(url).includes('/api/health')) return makeResponse(VOICE_HEALTH)
      return makeResponse({ ok: true })
    }) as typeof fetch
    global.fetch = fetchMock

    const { default: VoicePanel } = await import('@/components/VoicePanel')
    render(<VoicePanel />)

    // Wait for health fetch to resolve so toggle is visible and enabled
    await waitFor(() => {
      expect(screen.getByText('Duplex stream')).toBeInTheDocument()
    }, { timeout: 3000 })

    const toggle = screen.getByRole('button', { name: /Toggle/i })
    await userEvent.click(toggle)

    await waitFor(() => {
      const calls = (fetchMock as ReturnType<typeof vi.fn>).mock.calls
      const patchCall = calls.find(([url, opts]: [string, RequestInit]) =>
        String(url).includes('/api/settings') && opts?.method === 'PATCH'
      )
      expect(patchCall).toBeDefined()
    }, { timeout: 3000 })
  })

  it('shows offline fallback when health fetch fails', async () => {
    global.fetch = vi.fn(() => Promise.reject(new Error('offline'))) as typeof fetch

    const { default: VoicePanel } = await import('@/components/VoicePanel')
    render(<VoicePanel />)

    await waitFor(() => {
      expect(screen.getByText(/Hlasové API není dostupné/i)).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})
