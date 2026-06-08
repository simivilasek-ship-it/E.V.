import { useEffect } from 'react'
import { useJarvis } from '../store/jarvis'

const LEVEL_COLORS = {
  info: '#7ea8d4', success: '#10b981', warning: '#fbbf24', error: '#ef4444',
}

function FeedRow({ entry }) {
  const col = LEVEL_COLORS[entry.level] || '#7ea8d4'
  const time = entry.time || new Date((entry.ts || 0) * 1000).toLocaleTimeString('cs', { hour: '2-digit', minute: '2-digit' })

  return (
    <div style={{
      display: 'flex', gap: 10, padding: '6px 0',
      borderBottom: '1px solid #0b1220', animation: 'fadeIn .3s ease',
    }}>
      <span style={{ color: '#475569', fontSize: 10, width: 36, flexShrink: 0 }}>{time}</span>
      <div style={{
        width: 6, height: 6, borderRadius: '50%', background: col,
        marginTop: 5, flexShrink: 0, boxShadow: `0 0 6px ${col}88`,
      }} />
      <div style={{ flex: 1 }}>
        <span style={{ fontSize: 12, color: '#e2f0ff' }}>{entry.message}</span>
        {entry.detail && (
          <div style={{ fontSize: 10, color: '#475569', marginTop: 2 }}>{entry.detail}</div>
        )}
      </div>
    </div>
  )
}

function ProactiveCard({ sug, onDismiss }) {
  const sev = sug.severity === 'error' ? '#ef4444' : sug.severity === 'warning' ? '#fbbf24' : '#00d4ff'
  return (
    <div style={{
      background: '#0b1220', border: `1px solid ${sev}44`, borderRadius: 8,
      padding: '12px 14px', marginBottom: 8,
    }}>
      <div style={{ fontSize: 13, color: '#e2f0ff', fontWeight: 500 }}>{sug.title}</div>
      {sug.detail && <div style={{ fontSize: 11, color: '#475569', marginTop: 4 }}>{sug.detail}</div>}
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        {sug.action_label && (
          <button style={{
            padding: '4px 12px', background: `${sev}22`, border: `1px solid ${sev}55`,
            borderRadius: 4, color: sev, fontSize: 10, cursor: 'pointer',
          }}>{sug.action_label}</button>
        )}
        <button onClick={() => onDismiss(sug.id)} style={{
          padding: '4px 10px', background: 'transparent', border: '1px solid #1a3050',
          borderRadius: 4, color: '#475569', fontSize: 10, cursor: 'pointer',
        }}>Zavřít</button>
      </div>
    </div>
  )
}

export default function ActivityFeed({ compact = false }) {
  const feed = useJarvis(s => s.activityFeed)
  const suggestions = useJarvis(s => s.proactiveSuggestions)
  const connectActivity = useJarvis(s => s.connectActivity)
  const dismissSuggestion = useJarvis(s => s.dismissSuggestion)

  useEffect(() => { connectActivity() }, [connectActivity])

  if (compact) {
    return (
      <div style={{ fontSize: 11 }}>
        {feed.slice(-5).reverse().map((e, i) => (
          <div key={i} style={{ color: '#7ea8d4', padding: '3px 0' }}>
            <span style={{ color: '#475569' }}>{e.time}</span> {e.message}
          </div>
        ))}
        {feed.length === 0 && <span style={{ color: '#2d3748' }}>Čekám na aktivitu…</span>}
      </div>
    )
  }

  return (
    <div>
      {suggestions.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ color: '#475569', fontSize: 9, letterSpacing: '.15em', marginBottom: 8 }}>
            PROAKTIVNÍ NÁVRHY
          </div>
          {suggestions.map(s => (
            <ProactiveCard key={s.id} sug={s} onDismiss={dismissSuggestion} />
          ))}
        </div>
      )}

      <div style={{
        background: '#0b1220', border: '1px solid #1a3050', borderRadius: 8,
        padding: '12px 14px',
        maxHeight: compact ? 160 : 500, overflowY: 'auto',
      }}>
        <div style={{ color: '#475569', fontSize: 9, letterSpacing: '.15em', marginBottom: 10 }}>
          AGENT ACTIVITY FEED
        </div>
        {feed.length === 0
          ? <div style={{ color: '#2d3748', fontSize: 12 }}>Systém čeká na události…</div>
          : [...feed].reverse().map((e, i) => <FeedRow key={e.id || i} entry={e} />)
        }
      </div>
    </div>
  )
}
