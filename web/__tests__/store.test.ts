import { describe, it, expect } from 'vitest'
import { parseStatusToMode, normalizeAgents } from '@/store/ev'

describe('parseStatusToMode', () => {
  it('returns null for empty status', () => {
    expect(parseStatusToMode('')).toBeNull()
  })

  it('detects agent mode', () => {
    expect(parseStatusToMode('🤖 agent graph')).toBe('agent')
    expect(parseStatusToMode('Agent plánuje kroky')).toBe('agent')
  })

  it('detects action mode', () => {
    expect(parseStatusToMode('⚡ Provádím příkaz')).toBe('akce')
  })

  it('detects copilot mode', () => {
    expect(parseStatusToMode('💬 copilot')).toBe('copilot')
  })

  it('returns null for unrelated status', () => {
    expect(parseStatusToMode('idle')).toBeNull()
  })
})

describe('normalizeAgents', () => {
  it('passes through a list of agents', () => {
    const out = normalizeAgents([{ name: 'system_monitor', running: true }])
    expect(out).toEqual([{ name: 'system_monitor', running: true }])
  })

  it('converts a dict keyed by name into a list', () => {
    const out = normalizeAgents({ cpu_monitor: { running: false, interval: 30 } })
    expect(out).toEqual([{ running: false, interval: 30, name: 'cpu_monitor' }])
  })

  it('returns empty array for invalid input', () => {
    expect(normalizeAgents(null)).toEqual([])
    expect(normalizeAgents('x')).toEqual([])
  })
})
