'use client'

import { useEffect, useState } from 'react'
import { apiUrl } from '@/lib/api'

const TYPE_COLORS: Record<string, string> = {
  'git.commit': 'var(--green)', 'git.push': 'var(--blue)',
  'app.open': 'var(--purple)', 'build.fail': 'var(--red)',
  'command.done': 'var(--green)', 'release.create': 'var(--green)',
}

interface ActivityEvent {
  id: string
  type: string
  title: string
  detail?: string
  project?: string
  ts: number
  time?: string
}

interface DailySummary {
  summary?: string[]
  commits?: number
  builds_failed?: number
  releases?: number
  total_hours?: number
}

export default function WorkTimeline() {
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [summary, setSummary] = useState<DailySummary | null>(null)
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [querying, setQuerying] = useState(false)

  const refresh = async () => {
    try {
      setLoading(true)
      const res = await fetch(apiUrl('/api/activity/today'))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const d = await res.json()
      setEvents(d.events || [])
      setSummary(d.summary || null)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Backend offline')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    const iv = setInterval(refresh, 15000)
    return () => clearInterval(iv)
  }, [])

  const ask = async () => {
    if (!query.trim()) return
    setQuerying(true)
    try {
      const res = await fetch(apiUrl(`/api/activity/query?q=${encodeURIComponent(query)}`))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const d = await res.json()
      setAnswer(d.answer || '')
    } catch {
      setAnswer('⚠ Backend offline — nelze odpovědět')
    } finally {
      setQuerying(false)
    }
  }

  return (
    <div className="w-full max-w-2xl font-mono text-[var(--text)]">
      <div className="flex items-center justify-between mb-3">
        <div className="text-[9px] tracking-widest uppercase" style={{ color: 'var(--muted)' }}>
          Work Timeline — co jsi dělal dnes
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="text-xs px-2 py-1 rounded hover:bg-white/5 transition-colors"
          style={{ color: 'var(--muted)' }}
          title="Obnovit"
        >
          {loading ? '⏳' : '↻ refresh'}
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center p-8">
          <div className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full" />
        </div>
      )}

      {error && !loading && (
        <div className="p-4 text-amber-400 text-sm">⚠ {error} — backend může být offline</div>
      )}

      {!loading && !error && summary && (
        <div className="card p-5 mb-4">
          <div className="text-[9px] tracking-widest uppercase mb-3" style={{ color: 'var(--muted)' }}>Dnes — přehled</div>
          {summary.summary?.length ? summary.summary.map((line, i) => (
            <div key={i} className="text-[15px] font-medium mb-1">{line}</div>
          )) : <div className="text-sm" style={{ color: 'var(--muted)' }}>Zatím žádná aktivita</div>}
          <div className="flex gap-6 mt-4 flex-wrap">
            {summary.commits ? <Stat label="Commits" value={summary.commits} /> : null}
            {summary.builds_failed ? <Stat label="Build fail" value={summary.builds_failed} /> : null}
            {summary.releases ? <Stat label="Releases" value={summary.releases} /> : null}
            {summary.total_hours ? <Stat label="Hodin" value={summary.total_hours} /> : null}
          </div>
        </div>
      )}

      {!loading && (
        <div className="card p-3 mb-4 flex gap-2">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && ask()}
            placeholder="Co jsem dělal minulý týden? Na čem jsem skončil?"
            className="flex-1 bg-transparent border rounded px-3 py-2 text-sm outline-none"
            style={{ borderColor: 'var(--border)' }}
          />
          <button onClick={ask} disabled={querying} className="btn-primary text-xs px-3">
            {querying ? '…' : 'Zeptat'}
          </button>
        </div>
      )}

      {answer && (
        <div className="card p-4 mb-4 text-sm whitespace-pre-wrap leading-relaxed">{answer}</div>
      )}

      {!loading && (
        <div className="card p-4 max-h-[420px] overflow-y-auto">
          <div className="text-[9px] tracking-widest uppercase mb-3" style={{ color: 'var(--muted)' }}>
            Události ({events.length})
          </div>
          {events.length === 0 ? (
            <div className="text-sm" style={{ color: 'var(--muted)' }}>
              {error ? '⚠ Backend offline' : 'Čekám na aktivitu…'}
            </div>
          ) : [...events].reverse().map(e => (
            <div key={e.id} className="flex gap-3 py-2 border-b text-sm" style={{ borderColor: 'var(--border)' }}>
              <span className="text-[11px] w-10 shrink-0" style={{ color: 'var(--muted)' }}>
                {e.time || new Date(e.ts * 1000).toLocaleTimeString('cs', { hour: '2-digit', minute: '2-digit' })}
              </span>
              <div className="flex-1">
                <div className="text-xs" style={{ color: TYPE_COLORS[e.type] || 'var(--cyan)' }}>
                  {e.type?.replace('.', ' · ')}
                  {e.project && <span className="ml-2" style={{ color: 'var(--muted)' }}>{e.project}</span>}
                </div>
                <div>{e.title}</div>
                {e.detail && <div className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>{e.detail.slice(0, 120)}</div>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center">
      <div className="text-2xl font-bold" style={{ color: 'var(--cyan)' }}>{value}</div>
      <div className="text-[9px] tracking-wider uppercase" style={{ color: 'var(--muted)' }}>{label}</div>
    </div>
  )
}
