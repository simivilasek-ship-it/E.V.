'use client'

import { useCallback, useEffect, useState } from 'react'
import { apiUrl } from '@/lib/api'

interface AuditEntry {
  timestamp: number
  action: string
  params: Record<string, unknown>
  allowed: boolean
  reason: string
  user_text?: string
  result?: string
}

export default function AuditLogPanel() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'denied' | 'allowed'>('all')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch(apiUrl('/api/audit?limit=100'))
      const data = await r.json()
      setEntries(Array.isArray(data) ? data : [])
    } catch {
      setEntries([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [load])

  const shown = entries
    .slice()
    .reverse()
    .filter(e => {
      if (filter === 'denied') return !e.allowed
      if (filter === 'allowed') return e.allowed
      return true
    })

  return (
    <div className="card p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h3 className="font-hud text-[9px] tracking-widest uppercase" style={{ color: 'var(--muted)' }}>
          Security audit log
        </h3>
        <div className="flex gap-2">
          {(['all', 'denied', 'allowed'] as const).map(f => (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              className="text-[10px] px-2 py-1 rounded font-mono uppercase tracking-wider"
              style={{
                color: filter === f ? 'var(--cyan)' : 'var(--muted)',
                border: `1px solid ${filter === f ? 'var(--cyan)' : 'var(--border)'}`,
                background: filter === f ? 'rgba(0,200,255,.08)' : 'transparent',
              }}
            >
              {f}
            </button>
          ))}
          <button
            type="button"
            onClick={load}
            className="text-[10px] px-2 py-1 rounded font-mono"
            style={{ color: 'var(--muted)', border: '1px solid var(--border)' }}
          >
            ↻
          </button>
        </div>
      </div>

      <div
        className="rounded-lg overflow-auto font-mono text-[11px]"
        style={{ maxHeight: 360, border: '1px solid var(--border)', background: 'rgba(5,10,20,.6)' }}
      >
        {loading && <div className="p-4" style={{ color: 'var(--muted)' }}>Načítám…</div>}
        {!loading && shown.length === 0 && (
          <div className="p-4" style={{ color: 'var(--muted)' }}>Žádné záznamy</div>
        )}
        {!loading && shown.map((e, i) => {
          const ts = e.timestamp
            ? new Date(e.timestamp * 1000).toLocaleString('cs-CZ')
            : '—'
          return (
            <div
              key={`${e.timestamp}-${e.action}-${i}`}
              className="px-3 py-2 border-b"
              style={{ borderColor: 'var(--border)', color: e.allowed ? 'var(--text)' : '#f87171' }}
            >
              <div className="flex justify-between gap-2">
                <span style={{ color: 'var(--cyan)' }}>{e.action}</span>
                <span style={{ color: 'var(--muted)', fontSize: 10 }}>{ts}</span>
              </div>
              <div style={{ color: 'var(--muted)', fontSize: 10 }}>{e.reason}</div>
              {e.user_text && (
                <div style={{ color: 'var(--muted)', fontSize: 10, marginTop: 2 }}>„{e.user_text}"</div>
              )}
            </div>
          )
        })}
      </div>
      <p className="text-[10px]" style={{ color: 'var(--muted)' }}>
        Zdroj: ~/.jarvis_audit.jsonl · auto-refresh 15s
      </p>
    </div>
  )
}
