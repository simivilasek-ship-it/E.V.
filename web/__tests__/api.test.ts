import { describe, it, expect, afterEach } from 'vitest'
import { apiUrl, API_BASE } from '@/lib/api'

describe('apiUrl', () => {
  afterEach(() => {
    // API_BASE is module-level; tests only check path joining against current base
  })

  it('prefixes a slash when missing', () => {
    expect(apiUrl('health')).toBe(`${API_BASE}/health`)
  })

  it('keeps an absolute API path', () => {
    expect(apiUrl('/api/health')).toBe(`${API_BASE}/api/health`)
  })

  it('does not double the leading slash', () => {
    const url = apiUrl('/ws/audio')
    expect(url.startsWith('//')).toBe(false)
    expect(url.endsWith('/ws/audio')).toBe(true)
  })
})
