import { useEffect, useState } from 'react'

const API = import.meta.env.PROD
  ? `${window.location.protocol}//${window.location.host}`
  : 'http://localhost:8002'

const TYPE_COLORS = {
  'git.commit': '#10b981', 'git.push': '#3b82f6',
  'app.open': '#8b5cf6', 'app.focus': '#a78bfa',
  'docker.start': '#00d4ff', 'docker.stop': '#475569', 'docker.error': '#ef4444',
  'build.fail': '#ef4444', 'build.success': '#10b981',
  'command.run': '#f59e0b', 'command.done': '#10b981', 'command.error': '#ef4444',
  'release.create': '#22d3a5', 'proactive.alert': '#fbbf24',
  'agent.run_start': '#8b5cf6', 'agent.step': '#3b82f6',
  'mission.complete': '#22d3a5',
}

const TYPE_ICONS = {
  'git.commit': '⬡', 'git.push': '↑', 'app.open': '◉', 'app.focus': '◎',
  'docker.start': '🐳', 'build.fail': '✗', 'build.success': '✓',
  'command.run': '▶', 'release.create': '🚀', 'proactive.alert': '⚡',
}

function SummaryCard({ summary }) {
  if (!summary) return null
  return (
    <div style={{
      background: 'linear-gradient(135deg, #0b1220 0%, #0f1a2e 100%)',
      border: '1px solid #1a3050', borderRadius: 10, padding: '18px 22px',
      marginBottom: 16,
    }}>
      <div style={{ color: '#475569', fontSize: 9, letterSpacing: '.15em', marginBottom: 10 }}>
        DNES — PŘEHLED
      </div>
      {summary.summary?.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {summary.summary.map((line, i) => (
            <div key={i} style={{ fontSize: 15, color: '#e2f0ff', fontWeight: 500 }}>
              {line}
            </div>
          ))}
        </div>
      ) : (
        <div style={{ color: '#475569', fontSize: 13 }}>Zatím žádná aktivita dnes</div>
      )}
      <div style={{ display: 'flex', gap: 16, marginTop: 14, flexWrap: 'wrap' }}>
        {[
          ['Commits', summary.commits],
          ['Build fail', summary.builds_failed],
          ['Releases', summary.releases],
          ['Hodin', summary.total_hours],
        ].map(([label, val]) => val > 0 && (
          <div key={label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#00d4ff' }}>{val}</div>
            <div style={{ fontSize: 9, color: '#475569', letterSpacing: '.1em' }}>{label.toUpperCase()}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function EventRow({ event }) {
  const col = TYPE_COLORS[event.type] || '#4a6a8a'
  const icon = TYPE_ICONS[event.type] || '•'
  const time = event.time || new Date(event.ts * 1000).toLocaleTimeString('cs', { hour: '2-digit', minute: '2-digit' })

  return (
    <div style={{ display: 'flex', gap: 10, padding: '8px 0', borderBottom: '1px solid #0b1220' }}>
      <span style={{ color: '#475569', fontSize: 11, width: 38, flexShrink: 0, paddingTop: 2 }}>{time}</span>
      <span style={{ fontSize: 13, width: 20, flexShrink: 0 }}>{icon}</span>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 12, color: col, letterSpacing: '.05em' }}>
          {event.type?.replace('.', ' · ')}
          {event.project && <span style={{ color: '#475569', marginLeft: 8 }}>{event.project}</span>}
        </div>
        <div style={{ fontSize: 13, color: '#e2f0ff', marginTop: 2 }}>{event.title}</div>
        {event.detail && (
          <div style={{ fontSize: 11, color: '#475569', marginTop: 2 }}>{event.detail.slice(0, 120)}</div>
        )}
      </div>
    </div>
  )
}

export default function WorkTimeline() {
  const [events, setEvents] = useState([])
  const [summary, setSummary] = useState(null)
  const [query, setQuery] = useState('')
  const [answer, setAnswer] = useState('')

  const refresh = () => {
    fetch(`${API}/api/activity/today`).then(r => r.json()).then(d => {
      setEvents(d.events || [])
      setSummary(d.summary || null)
    }).catch(() => {})
  }

  useEffect(() => {
    refresh()
    const iv = setInterval(refresh, 15000)
    return () => clearInterval(iv)
  }, [])

  const askMemory = () => {
    if (!query.trim()) return
    fetch(`${API}/api/activity/query?q=${encodeURIComponent(query)}`)
      .then(r => r.json())
      .then(d => setAnswer(d.answer || ''))
      .catch(() => setAnswer('Chyba dotazu'))
  }

  return (
    <div style={{ maxWidth: 720, width: '100%', padding: '0 4px' }}>
      <div style={{ color: '#475569', fontSize: 9, letterSpacing: '.15em', marginBottom: 12 }}>
        WORK TIMELINE — co jsi dělal dnes
      </div>

      <SummaryCard summary={summary} />

      {/* Memory query */}
      <div style={{
        background: '#0b1220', border: '1px solid #1a3050', borderRadius: 8,
        padding: '12px 14px', marginBottom: 14, display: 'flex', gap: 8,
      }}>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && askMemory()}
          placeholder="Co jsem dělal minulý týden? Na čem jsem skončil?"
          style={{
            flex: 1, background: '#050a15', border: '1px solid #1a3050',
            borderRadius: 5, padding: '8px 12px', color: '#e2f0ff', fontSize: 12,
            outline: 'none',
          }}
        />
        <button onClick={askMemory} style={{
          padding: '8px 14px', background: '#00d4ff22', border: '1px solid #00d4ff55',
          borderRadius: 5, color: '#00d4ff', fontSize: 11, cursor: 'pointer',
          letterSpacing: '.08em',
        }}>ZEPTAT</button>
      </div>
      {answer && (
        <div style={{
          background: '#0b1220', border: '1px solid #00d4ff33', borderRadius: 8,
          padding: '12px 16px', marginBottom: 14, fontSize: 13, color: '#e2f0ff',
          whiteSpace: 'pre-wrap', lineHeight: 1.6,
        }}>{answer}</div>
      )}

      {/* Event list */}
      <div style={{
        background: '#0b1220', border: '1px solid #1a3050', borderRadius: 8,
        padding: '12px 16px', maxHeight: 420, overflowY: 'auto',
      }}>
        <div style={{ color: '#475569', fontSize: 9, letterSpacing: '.15em', marginBottom: 10 }}>
          UDÁLOSTI ({events.length})
        </div>
        {events.length === 0
          ? <div style={{ color: '#2d3748', fontSize: 12 }}>Čekám na aktivitu…</div>
          : [...events].reverse().map(e => <EventRow key={e.id} event={e} />)
        }
      </div>
    </div>
  )
}
