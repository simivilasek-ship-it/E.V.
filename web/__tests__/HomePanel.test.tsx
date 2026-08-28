import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

vi.mock('@/store/ev', () => {
  const state = {
    orbState: 'idle',
    connStatus: 'connected',
    system: { cpu: 12, ram: 40, disk: 50 },
  }
  return { useEV: (selector: (s: typeof state) => unknown) => selector(state) }
})

describe('HomePanel', () => {
  it('shows the core and opens chat from the corner button', async () => {
    const { default: HomePanel } = await import('@/components/HomePanel')
    const onOpenChat = vi.fn()
    render(<HomePanel onOpenChat={onOpenChat} />)

    expect(screen.getByTestId('home-stage')).toBeInTheDocument()
    expect(screen.getByTestId('jarvis-core')).toBeInTheDocument()
    await userEvent.click(screen.getByTestId('open-chat'))
    expect(onOpenChat).toHaveBeenCalled()
    expect(screen.queryByTestId('home-tap-hint')).not.toBeInTheDocument()
  })

  it('asks for a tap so she can say hello', async () => {
    const { default: HomePanel } = await import('@/components/HomePanel')
    render(<HomePanel onOpenChat={() => undefined} needsTap />)
    expect(screen.getByTestId('home-tap-hint')).toHaveTextContent('Klepni kdekoli')
  })
})
