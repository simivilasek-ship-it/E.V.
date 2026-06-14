import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

// Suppress React's error boundary console.error output in test logs
beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

// ── Helpers ────────────────────────────────────────────────────────────────────

function BrokenChild(): React.ReactElement {
  throw new Error('Test error message')
}

function SafeChild() {
  return <div data-testid="safe-child">Safe content</div>
}

// ── Tests ──────────────────────────────────────────────────────────────────────

describe('ErrorBoundary', () => {
  it('renders children normally when no error is thrown', async () => {
    const { default: ErrorBoundary } = await import('@/components/ErrorBoundary')
    render(
      <ErrorBoundary>
        <SafeChild />
      </ErrorBoundary>
    )

    expect(screen.getByTestId('safe-child')).toBeInTheDocument()
    expect(screen.getByText('Safe content')).toBeInTheDocument()
  })

  it('catches error and shows fallback UI', async () => {
    const { default: ErrorBoundary } = await import('@/components/ErrorBoundary')
    render(
      <ErrorBoundary>
        <BrokenChild />
      </ErrorBoundary>
    )

    expect(screen.getByText('KOMPONENTA SELHALA')).toBeInTheDocument()
    expect(screen.getByText('Test error message')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ZKUSIT ZNOVU/i })).toBeInTheDocument()
  })

  it('reset button clears the error state', async () => {
    const { default: ErrorBoundary } = await import('@/components/ErrorBoundary')

    // We need a toggleable broken child to verify reset re-renders children
    let shouldThrow = true
    function MaybeThrow() {
      if (shouldThrow) throw new Error('Controlled error')
      return <div data-testid="recovered">Recovered</div>
    }

    const { rerender } = render(
      <ErrorBoundary>
        <MaybeThrow />
      </ErrorBoundary>
    )

    // Error fallback should be visible
    expect(screen.getByText('KOMPONENTA SELHALA')).toBeInTheDocument()

    // Stop throwing before clicking reset so children render successfully
    shouldThrow = false

    const resetBtn = screen.getByRole('button', { name: /ZKUSIT ZNOVU/i })
    await userEvent.click(resetBtn)

    // After reset the boundary clears its error state; re-render with safe child
    rerender(
      <ErrorBoundary>
        <SafeChild />
      </ErrorBoundary>
    )

    expect(screen.getByTestId('safe-child')).toBeInTheDocument()
  })
})
