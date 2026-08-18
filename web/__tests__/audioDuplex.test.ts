import { describe, it, expect } from 'vitest'
import { downsampleTo16k, pcmRms } from '@/lib/audioDuplex'

describe('downsampleTo16k', () => {
  it('converts same-rate float samples to int16', () => {
    const input = new Float32Array([0, 0.5, -0.5, 1, -1])
    const out = downsampleTo16k(input, 16000)
    expect(out).toBeInstanceOf(Int16Array)
    expect(out.length).toBe(5)
    expect(out[0]).toBe(0)
    expect(out[1]).toBeGreaterThan(0)
    expect(out[2]).toBeLessThan(0)
  })

  it('downsamples 48 kHz to 16 kHz', () => {
    const input = new Float32Array(4800)
    input.fill(0.1)
    const out = downsampleTo16k(input, 48000)
    expect(out.length).toBe(1600)
  })
})

describe('pcmRms', () => {
  it('returns 0 for silence', () => {
    expect(pcmRms(new Float32Array(32))).toBe(0)
  })

  it('returns a positive value for a signal', () => {
    const input = new Float32Array([0.5, -0.5, 0.5, -0.5])
    expect(pcmRms(input)).toBeGreaterThan(0.4)
  })

  it('handles empty input', () => {
    expect(Number.isFinite(pcmRms(new Float32Array(0)))).toBe(true)
  })
})
