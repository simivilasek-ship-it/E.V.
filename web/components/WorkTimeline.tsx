'use client'

import { useEffect, useState } from 'react'
import { apiUrl } from '@/lib/api'

const TYPE_COLORS: Record<string, string> = {
  'git.commit': '#10b981', 'git.push': '#3b82f6',
  'app.open': '#8b5cf6', 'build.fail': '#ef4444',
  'command.done': '#10b981', 'release.create': '#22d3a5',
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

  const refresh = () => {
    fetch(apiUrl('/api/activity/today'))
      .then(r => r.json())
      .then(d => { setEvents(d.events || []); setSummary(d.summary || null) })
      .catch(() => {})
  }

  useEffect(() => {
    refresh()
    const iv = setInterval(refresh, 15000)
    return () => clearInterval(iv)
  }, [])

  const ask = () => {
    if (!query.trim()) return
    fetch(apiUrl(`/api/activity/query?q=${encodeURIComponent(query)}`))
      .then(r => r.json())
      .then(d => setAnswer(d.answer || ''))
      .catch(() => setAnswer('Chyba dotazu'))
  }

  return (
    <div className="w-full max-w-2xl font-mono text-[var(--text)]">
      <div className="text-[9px] tracking-widest uppercase mb-3" style={{ color: 'var(--muted)' }}>
        Work Timeline — co jsi dělal dnes
      </div>

      {summary && (
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

      <div className="card p-3 mb-4 flex gap-2">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && ask()}
          placeholder="Co jsem dělal minulý týden? Na čem jsem skončil?"
          className="flex-1 bg-transparent border rounded px-3 py-2 text-sm outline-none"
          style={{ borderColor: 'var(--border)' }}
        />
        <button onClick={ask} className="btn-primary text-xs px-3">Zeptat</button>
      </div>

      {answer && (
        <div className="card p-4 mb-4 text-sm whitespace-pre-wrap leading-relaxed">{answer}</div>
      )}

      <div className="card p-4 max-h-[420px] overflow-y-auto">
        <div className="text-[9px] tracking-widest uppercase mb-3" style={{ color: 'var(--muted)' }}>
          Události ({events.length})
        </div>
        {events.length === 0 ? (
          <div className="text-sm" style={{ color: 'var(--muted)' }}>Čekám na aktivitu…</div>
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
