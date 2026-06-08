'use client'

import { useEffect } from 'react'
import { useJarvis } from '@/store/jarvis'

const LEVEL_COLORS: Record<string, string> = {
  info: 'var(--muted)', success: 'var(--green)', warning: 'var(--amber)', error: 'var(--red)',
}

interface FeedEntry {
  id?: string
  message: string
  detail?: string
  level?: string
  time?: string
}

interface Suggestion {
  id: string
  title: string
  detail?: string
  action?: string
  action_label?: string
  severity?: string
}

function handleProactiveAction(action: string, sendCommand: (t: string) => void) {
  if (action === 'show_processes') sendCommand('ukaž běžící procesy')
  else if (action === 'search_github_issues') sendCommand('vyhledej podobný issue na GitHubu pro poslední build error')
  else if (action === 'restart_container') sendCommand('restartuj docker container')
}

function FeedRow({ entry }: { entry: FeedEntry }) {
  const col = LEVEL_COLORS[entry.level || 'info'] || 'var(--muted)'
  return (
    <div className="flex gap-3 py-1.5 border-b text-sm" style={{ borderColor: 'var(--border)' }}>
      <span className="text-[10px] w-9 shrink-0" style={{ color: 'var(--muted)' }}>{entry.time}</span>
      <span className="w-1.5 h-1.5 rounded-full mt-2 shrink-0" style={{ background: col }} />
      <div className="flex-1">
        <span>{entry.message}</span>
        {entry.detail && <div className="text-[10px] mt-0.5" style={{ color: 'var(--muted)' }}>{entry.detail}</div>}
      </div>
    </div>
  )
}

function ProactiveCard({ sug, onDismiss, onAction }: {
  sug: Suggestion
  onDismiss: (id: string) => void
  onAction: (action: string) => void
}) {
  const sev = sug.severity === 'error' ? 'var(--red)' : sug.severity === 'warning' ? 'var(--amber)' : 'var(--cyan)'
  return (
    <div className="card p-3 mb-2" style={{ borderColor: `${sev}44` }}>
      <div className="font-medium text-sm">{sug.title}</div>
      {sug.detail && <div className="text-xs mt-1" style={{ color: 'var(--muted)' }}>{sug.detail}</div>}
      <div className="flex gap-2 mt-2">
        {sug.action && sug.action_label && (
          <button
            onClick={() => onAction(sug.action!)}
            className="text-[10px] px-3 py-1 rounded border"
            style={{ color: sev, borderColor: `${sev}55` }}
          >{sug.action_label}</button>
        )}
        <button onClick={() => onDismiss(sug.id)} className="text-[10px] px-2 py-1 btn-ghost">Zavřít</button>
      </div>
    </div>
  )
}

export default function ActivityFeed({ compact = false }: { compact?: boolean }) {
  const feed = useJarvis(s => s.activityFeed)
  const suggestions = useJarvis(s => s.proactiveSuggestions)
  const connectActivity = useJarvis(s => s.connectActivity)
  const dismissSuggestion = useJarvis(s => s.dismissSuggestion)
  const sendCommand = useJarvis(s => s.sendCommand)

  useEffect(() => { connectActivity() }, [connectActivity])

  if (compact) {
    return (
      <div className="text-[11px]">
        {feed.slice(-5).reverse().map((e, i) => (
          <div key={i} style={{ color: 'var(--muted)' }}>
            <span style={{ color: 'var(--muted)' }}>{e.time}</span> {e.message}
          </div>
        ))}
        {feed.length === 0 && <span style={{ color: 'var(--muted)' }}>Čekám na aktivitu…</span>}
      </div>
    )
  }

  return (
    <div className="w-full max-w-2xl">
      {suggestions.length > 0 && (
        <div className="mb-4">
          <div className="text-[9px] tracking-widest uppercase mb-2" style={{ color: 'var(--muted)' }}>Proaktivní návrhy</div>
          {suggestions.map(s => (
            <ProactiveCard
              key={s.id}
              sug={s}
              onDismiss={dismissSuggestion}
              onAction={a => handleProactiveAction(a, sendCommand)}
            />
          ))}
        </div>
      )}
      <div className="card p-4 max-h-[500px] overflow-y-auto">
        <div className="text-[9px] tracking-widest uppercase mb-3" style={{ color: 'var(--muted)' }}>Agent Activity Feed</div>
        {feed.length === 0 ? (
          <div className="text-sm" style={{ color: 'var(--muted)' }}>Systém čeká na události…</div>
        ) : [...feed].reverse().map((e, i) => <FeedRow key={e.id || i} entry={e} />)}
      </div>
    </div>
  )
}
