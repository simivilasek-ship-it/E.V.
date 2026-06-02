'use client'
import { useEffect, useState } from 'react'
import { useJarvis, type Message } from '@/store/jarvis'

// ── Recent conversations ──────────────────────────────
function RecentConversations({ messages }: { messages: Message[] }) {
  const recent = messages.slice(-3)
  if (recent.length === 0) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontFamily: 'var(--font-hud)', fontSize: 9, letterSpacing: '.15em', color: 'var(--muted)', marginBottom: 2 }}>
        NEDÁVNÉ KONVERZACE
      </div>
      {recent.map(m => (
        <div key={m.id} style={{
          display: 'flex', gap: 8, alignItems: 'flex-start',
          padding: '7px 10px',
          background: 'rgba(255,255,255,.02)',
          border: '1px solid rgba(255,255,255,.06)',
          borderRadius: 8,
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
            color: m.sender === 'user' ? 'rgba(99,102,241,.8)' : 'var(--cyan)',
            flexShrink: 0, paddingTop: 1,
          }}>
            {m.sender === 'user' ? 'Vy' : 'J'}
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--muted)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
          }}>
            {m.text || '…'}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Agent status widget ───────────────────────────────
interface AgentInfo {
  name: string
  status: string
  lastRun?: string
}

function AgentStatus() {
  const agents = useJarvis(s => s.agents) as Record<string, { status?: string; last?: string }>

  const list: AgentInfo[] = Object.entries(agents).slice(0, 4).map(([name, v]) => ({
    name,
    status: v?.status ?? 'unknown',
    lastRun: v?.last,
  }))

  const fallback: AgentInfo[] = [
    { name: 'CPU Monitor', status: 'idle' },
    { name: 'RAM Monitor', status: 'idle' },
    { name: 'Disk Monitor', status: 'idle' },
    { name: 'Ollama Agent', status: 'idle' },
  ]

  const display = list.length > 0 ? list : fallback

  const dot = (s: string) => {
    if (s === 'running') return '#22d3a5'
    if (s === 'error')   return '#f43f5e'
    return 'var(--muted)'
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontFamily: 'var(--font-hud)', fontSize: 9, letterSpacing: '.15em', color: 'var(--muted)', marginBottom: 2 }}>
        AGENT STATUS
      </div>
      {display.map(a => (
        <div key={a.name} style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '6px 10px',
          background: 'rgba(255,255,255,.02)',
          border: '1px solid rgba(255,255,255,.06)',
          borderRadius: 8,
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: dot(a.status),
            boxShadow: a.status === 'running' ? `0 0 6px ${dot(a.status)}` : 'none',
            flexShrink: 0,
          }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text)', flex: 1 }}>{a.name}</span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 9,
            color: dot(a.status),
            textTransform: 'uppercase',
          }}>{a.status}</span>
        </div>
      ))}
    </div>
  )
}

// ── Last 5 commands ───────────────────────────────────
function LastCommands({ messages }: { messages: Message[] }) {
  const cmds = messages.filter(m => m.sender === 'user').slice(-5).reverse()

  if (cmds.length === 0) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div style={{ fontFamily: 'var(--font-hud)', fontSize: 9, letterSpacing: '.15em', color: 'var(--muted)', marginBottom: 2 }}>
          POSLEDNÍ PŘÍKAZY
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--muted)', padding: '8px 10px' }}>
          Žádné příkazy zatím…
        </div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontFamily: 'var(--font-hud)', fontSize: 9, letterSpacing: '.15em', color: 'var(--muted)', marginBottom: 2 }}>
        POSLEDNÍ PŘÍKAZY
      </div>
      {cmds.map((m, i) => (
        <div key={m.id} style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '6px 10px',
          background: 'rgba(255,255,255,.02)',
          border: '1px solid rgba(255,255,255,.05)',
          borderRadius: 8,
        }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'rgba(255,255,255,.2)', flexShrink: 0, width: 12, textAlign: 'right' }}>
            {i + 1}
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--muted)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
          }}>
            {m.text}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Open windows (from API) ───────────────────────────
interface WindowInfo {
  title: string
  app: string
}

function OpenWindows() {
  const [windows, setWindows] = useState<WindowInfo[]>([])

  useEffect(() => {
    fetch('/api/windows')
      .then(r => r.json())
      .then((d: WindowInfo[] | { windows?: WindowInfo[] }) => {
        const list = Array.isArray(d) ? d : (d.windows ?? [])
        setWindows(list.slice(0, 5))
      })
      .catch(() => {})
  }, [])

  if (windows.length === 0) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ fontFamily: 'var(--font-hud)', fontSize: 9, letterSpacing: '.15em', color: 'var(--muted)', marginBottom: 2 }}>
        OTEVŘENÁ OKNA
      </div>
      {windows.map((w, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '6px 10px',
          background: 'rgba(255,255,255,.02)',
          border: '1px solid rgba(255,255,255,.05)',
          borderRadius: 8,
        }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: '#a855f7', flexShrink: 0 }}>
            {w.app || '□'}
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--muted)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
          }}>
            {w.title}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Main CenterDashboard ──────────────────────────────
export default function CenterDashboard() {
  const messages = useJarvis(s => s.messages)

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      gap: 16,
      width: '100%',
      padding: '12px 0',
    }}>
      {/* Agent Status */}
      <div style={{
        padding: '14px 14px',
        background: 'rgba(255,255,255,.02)',
        border: '1px solid rgba(0,200,255,.08)',
        borderRadius: 12,
      }}>
        <AgentStatus />
      </div>

      {/* Last Commands */}
      <div style={{
        padding: '14px 14px',
        background: 'rgba(255,255,255,.02)',
        border: '1px solid rgba(0,200,255,.08)',
        borderRadius: 12,
      }}>
        <LastCommands messages={messages} />
      </div>

      {/* Recent Conversations */}
      <div style={{
        padding: '14px 14px',
        background: 'rgba(255,255,255,.02)',
        border: '1px solid rgba(0,200,255,.08)',
        borderRadius: 12,
      }}>
        <RecentConversations messages={messages} />
        {messages.length === 0 && (
          <div style={{ fontFamily: 'var(--font-hud)', fontSize: 9, letterSpacing: '.15em', color: 'var(--muted)', marginBottom: 8 }}>
            NEDÁVNÉ KONVERZACE
          </div>
        )}
        {messages.length === 0 && (
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--muted)', padding: '8px 10px' }}>
            Žádné zprávy zatím…
          </div>
        )}
        <OpenWindows />
      </div>
    </div>
  )
}
