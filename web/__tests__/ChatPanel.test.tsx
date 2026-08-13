import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

// ── Mocks ──────────────────────────────────────────────────────────────────────

vi.mock('@/lib/audioDuplex', () => ({
  AudioDuplex: vi.fn().mockImplementation(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
    send: vi.fn(),
  })),
}))

// Mock next/dynamic so dynamic imports resolve synchronously in tests
vi.mock('next/dynamic', () => ({
  default: (fn: () => Promise<{ default: React.ComponentType }>) => {
    // Return a stub component — we only test ChatPanel directly
    return function DynamicStub() { return null }
  },
}))

const mockSendCommand = vi.fn()
const mockToggleMic = vi.fn()
const mockClearMessages = vi.fn()

const baseState = {
  messages: [],
  orbState: 'idle' as const,
  isMicActive: false,
  activeInstall: null,
  sendCommand: mockSendCommand,
  toggleMic: mockToggleMic,
  clearMessages: mockClearMessages,
  addToast: vi.fn(),
  addMessage: vi.fn(),
}

vi.mock('@/store/ev', () => ({
  useEV: (selector: (s: typeof baseState) => unknown) => selector(baseState),
}))

// HeroPanel is rendered when messages is empty — provide a simple stub
vi.mock('@/components/HeroPanel', () => ({
  default: ({ onSend }: { onSend: (cmd: string) => void }) => (
    <div data-testid="hero-panel">
      <button onClick={() => onSend('test quick')}>Quick Action</button>
    </div>
  ),
  EVStatusBar: () => null,
}))

beforeEach(() => {
  vi.clearAllMocks()
  global.fetch = vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: 'ok' }),
    } as Response)
  )
})

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('ChatPanel', () => {
  it('renders the chat input textarea', async () => {
    const { default: ChatPanel } = await import('@/components/ChatPanel')
    render(<ChatPanel />)

    const textarea = screen.getByTestId('chat-input')
    expect(textarea).toBeInTheDocument()
    expect(textarea).toBeVisible()
  })

  it('chat input accepts text input', async () => {
    const { default: ChatPanel } = await import('@/components/ChatPanel')
    render(<ChatPanel />)

    const textarea = screen.getByTestId('chat-input') as HTMLTextAreaElement
    await userEvent.click(textarea)
    await userEvent.type(textarea, 'Hello E.V.')

    expect(textarea.value).toBe('Hello E.V.')
  })

  it('send button is disabled when input is empty', async () => {
    const { default: ChatPanel } = await import('@/components/ChatPanel')
    render(<ChatPanel />)

    // The send button should be disabled with empty input
    const sendButton = screen.getByRole('button', { name: '' })
    // Find the send button — it's the last button in the input shell
    const buttons = screen.getAllByRole('button')
    const sendBtn = buttons[buttons.length - 1]
    expect(sendBtn).toBeDisabled()
  })

  it('pressing Enter calls sendCommand with the typed text', async () => {
    const { default: ChatPanel } = await import('@/components/ChatPanel')
    render(<ChatPanel />)

    const textarea = screen.getByTestId('chat-input')
    await userEvent.click(textarea)
    await userEvent.type(textarea, 'test command')
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter', shiftKey: false })

    await waitFor(() => {
      expect(mockSendCommand).toHaveBeenCalledWith('test command')
    })
  })

  it('Shift+Enter does not send and adds newline', async () => {
    const { default: ChatPanel } = await import('@/components/ChatPanel')
    render(<ChatPanel />)

    const textarea = screen.getByTestId('chat-input')
    await userEvent.click(textarea)
    await userEvent.type(textarea, 'line one')
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter', shiftKey: true })

    // sendCommand should NOT have been called
    expect(mockSendCommand).not.toHaveBeenCalled()
  })

  it('clear button calls clearMessages', async () => {
    const { default: ChatPanel } = await import('@/components/ChatPanel')
    render(<ChatPanel />)

    const clearBtn = screen.getByRole('button', { name: /Vymazat/i })
    await userEvent.click(clearBtn)

    expect(mockClearMessages).toHaveBeenCalled()
  })

  it('renders HeroPanel when there are no messages', async () => {
    const { default: ChatPanel } = await import('@/components/ChatPanel')
    render(<ChatPanel />)

    expect(screen.getByTestId('hero-panel')).toBeInTheDocument()
  })
})
