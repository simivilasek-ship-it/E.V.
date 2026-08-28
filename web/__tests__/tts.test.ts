import { describe, it, expect, vi, afterEach } from 'vitest'
import { playReplySpeech, subscribeTtsPlayback } from '@/lib/tts'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('playReplySpeech', () => {
  it('skips empty and error text', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    await playReplySpeech('')
    await playReplySpeech('⚠ chyba')
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('subscribeTtsPlayback', () => {
  it('notifies the current playback state immediately', () => {
    const seen: boolean[] = []
    const stop = subscribeTtsPlayback(on => { seen.push(on) })
    expect(seen[0]).toBe(false)
    stop()
  })
})
