'use client'
import { useEffect, useRef, useState } from 'react'
import { useJarvis } from '@/store/jarvis'
import CenterDashboard from './CenterDashboard'

// ── Status Bar ────────────────────────────────────────
interface StatusItem {
  label: string
  value: string
  color?: string
}

export function JarvisStatusBar() {
  const connStatus   = useJarvis(s => s.connStatus)
  const currentModel = useJarvis(s => s.currentModel)
  const plugins      = useJarvis(s => s.plugins) as Array<{ status?: string }>
  const [mcpCount, setMcpCount] = useState('—')
  const [agentStatus] = useState('Ready')

  useEffect(() => {
    fetch('/api/plugins')
      .then(r => r.json())
      .then((d: { healthy?: number; total?: number }) =>
        setMcpCount(`${d.healthy ?? '?'}/${d.total ?? '?'}`)
      )
      .catch(() => setMcpCount('—'))
  }, [])

  const online = connStatus === 'connected'

  const okPlugins = plugins.filter(p => p.status === 'ok').length
  const items: StatusItem[] = [
    { label: 'Model',   value: currentModel || 'qwen2.5:3b',                        color: '#00c8ff' },
    { label: 'Memory',  value: 'Active',                                             color: '#22d3a5' },
    { label: 'Plugins', value: `${okPlugins}/${plugins.length} OK`,                  color: '#a855f7' },
    { label: 'MCP',     value: mcpCount,                                             color: '#f59e0b' },
    { label: 'Agents',  value: agentStatus,                                          color: '#f59e0b' },
  ]

  return (
    <div className="glass-panel flex items-center gap-4 flex-wrap px-4 py-2.5 rounded-xl"
      style={{ border: '1px solid var(--border)' }}>
      <span className="status-pill" style={{ color: online ? 'var(--green)' : 'var(--red)' }}>
        <span className="w-2 h-2 rounded-full" style={{
          background: online ? 'var(--green)' : 'var(--red)',
          boxShadow: online ? '0 0 8px var(--green)' : 'none',
          animation: online ? 'pulseDot 2s infinite' : 'none',
        }} />
        {online ? 'Online' : 'Offline'}
      </span>
      {items.map(item => (
        <div key={item.label} className="flex items-center gap-1.5 font-mono text-[11px]">
          <span style={{ color: 'var(--muted)' }}>{item.label}</span>
          <span className="font-medium" style={{ color: item.color || 'var(--text)' }}>{item.value}</span>
        </div>
      ))}
    </div>
  )
}

// ── Hodiny živé ───────────────────────────────────────
function LiveClock() {
  const [t, setT] = useState('')
  const [d, setD] = useState('')
  useEffect(() => {
    const tick = () => {
      const n = new Date()
      setT(n.toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' }))
      setD(n.toLocaleDateString('cs-CZ', { weekday: 'long', day: 'numeric', month: 'long' }))
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])
  return (
    <div className="text-center">
      <div className="font-display text-5xl font-bold tracking-tight" style={{ color: 'var(--text)' }}>{t}</div>
      <div className="text-sm mt-1 capitalize" style={{ color: 'var(--muted)' }}>{d}</div>
    </div>
  )
}

// ── Mini metrika ──────────────────────────────────────
function MetricPill({ label, value, color, unit = '%' }: {
  label: string; value: number | string; color: string; unit?: string
}) {
  const numVal = typeof value === 'number' ? value : null
  const warn = numVal !== null && numVal > 85 ? 'var(--red)' : numVal !== null && numVal > 70 ? 'var(--amber)' : color
  return (
    <div className="card flex flex-col items-center gap-1 px-4 py-3">
      <div className="text-[10px] font-medium uppercase tracking-wider" style={{ color: 'var(--muted)' }}>{label}</div>
      <div className="font-mono text-xl font-bold" style={{ color: warn }}>
        {value}{typeof value === 'number' ? unit : ''}
      </div>
      {numVal !== null && (
        <div className="w-full h-1 rounded-full" style={{ background: 'rgba(255,255,255,.06)' }}>
          <div className="h-full rounded-full transition-all duration-700"
            style={{ width: `${Math.min(numVal, 100)}%`, background: warn, boxShadow: `0 0 6px ${warn}` }}/>
        </div>
      )}
    </div>
  )
}

// ── Quick action button ───────────────────────────────
function ActionBtn({ icon, label, cmd, onSend }: {
  icon: string; label: string; cmd: string; onSend: (c: string) => void
}) {
  const [hover, setHover] = useState(false)
  return (
    <button
      onClick={() => onSend(cmd)}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      className="card flex items-center gap-2.5 px-4 py-3 text-sm font-medium transition-all text-left"
      style={{
        borderColor: hover ? 'var(--border-accent)' : undefined,
        background: hover ? 'rgba(99,102,241,.08)' : undefined,
        transform: hover ? 'translateY(-1px)' : 'none',
      }}>
      <span className="text-xl">{icon}</span>
      <span>{label}</span>
    </button>
  )
}

// ── Active agents indicator ───────────────────────────
function AgentDot({ label, active }: { label: string; active: boolean }) {
  return (
    <div className="flex items-center gap-1.5 text-xs font-mono" style={{ color: active ? 'var(--green)' : 'var(--muted)' }}>
      <span className="w-1.5 h-1.5 rounded-full"
        style={{ background: active ? 'var(--green)' : 'var(--muted)', boxShadow: active ? '0 0 6px var(--green)' : 'none', animation: active ? 'pulseDot 2s ease-in-out infinite' : 'none' }}/>
      {label}
    </div>
  )
}

const QUICK_ACTIONS = [
  { icon: '💻', label: 'Otevři VS Code',     cmd: 'otevři vscode' },
  { icon: '📸', label: 'Screenshot',          cmd: 'screenshot' },
  { icon: '🌤️', label: 'Počasí Praha',       cmd: 'počasí Praha' },
  { icon: '⚽', label: 'Fotbal výsledky',     cmd: 'fotbal výsledky' },
  { icon: '🔍', label: 'Analyzuj projekt',    cmd: 'popiš aktivní okno a co dělám' },
  { icon: '🎵', label: 'Zahraj něco',         cmd: 'zahraj lofi hip hop' },
  { icon: '🖥️', label: 'Info o systému',     cmd: 'hardware info' },
  { icon: '🤖', label: 'Multi-agent analýza', cmd: 'multi-agent analyzuj systém' },
]

// ── Hero Panel ────────────────────────────────────────
export default function HeroPanel({ onSend }: { onSend: (cmd: string) => void }) {
  const system   = useJarvis(s => s.system)
  const isConn   = useJarvis(s => s.isConnected)
  const connStatus = useJarvis(s => s.connStatus)

  const [profile, setProfile] = useState<{ name: string; model: string }>({ name: '', model: '' })
  const wsRef = useRef<WebSocket | null>(null)

  // Načti profil (jméno, model)
  useEffect(() => {
    fetch('http://127.0.0.1:8002/api/profile')
      .then(r => r.ok ? r.json() : { name: '', model: '' })
      .then((d: { name?: string; model?: string }) => setProfile({ name: d.name || '', model: d.model || '' }))
      .catch(() => {})
  }, [])

  // Live metriky přes WS (pokud nejsou ze store)
  useEffect(() => {
    if (system.cpu > 0) return  // store už má data
    const ws = new WebSocket('ws://127.0.0.1:8002/ws/agents')
    wsRef.current = ws
    return () => ws.close()
  }, [system.cpu])

  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Dobré ráno'
    if (h < 18) return 'Dobrý den'
    return 'Dobrý večer'
  }

  return (
    <div className="flex flex-col items-center justify-center flex-1 gap-8 px-8 py-6 w-full max-w-205 mx-auto">

      {/* Hodiny */}
      <LiveClock />

      {/* Pozdrav + status */}
      <div className="text-center">
        <h1 className="text-2xl font-semibold" style={{ color: 'var(--text)' }}>
          {greeting()}{profile.name ? `, ${profile.name}` : ''}.
        </h1>
        <p className="mt-1.5 text-sm" style={{ color: 'var(--muted)' }}>
          Co chcete dnes udělat?
        </p>
      </div>

      {/* Live metriky */}
      <div className="grid grid-cols-4 gap-3 w-full">
        <MetricPill label="CPU" value={system.cpu} color="var(--cyan)" />
        <MetricPill label="RAM" value={system.ram} color="var(--purple)" />
        <MetricPill label="DISK" value={system.disk} color="var(--green)" />
        <MetricPill label="MODEL" value={profile.model || '—'} color="var(--amber)" unit="" />
      </div>

      {/* Quick actions */}
      <div className="w-full">
        <div className="text-xs font-medium uppercase tracking-wider mb-3" style={{ color: 'var(--muted)' }}>
          Rychlé akce
        </div>
        <div className="grid grid-cols-4 gap-2.5">
          {QUICK_ACTIONS.map(a => (
            <ActionBtn key={a.cmd} {...a} onSend={onSend} />
          ))}
        </div>
      </div>

      {/* Active agents + connection */}
      <div className="flex items-center gap-4 w-full justify-center flex-wrap">
        <AgentDot label="CPU monitor" active={isConn} />
        <AgentDot label="RAM monitor" active={isConn} />
        <AgentDot label="Disk monitor" active={isConn} />
        <AgentDot label="Ollama" active={isConn && system.cpu >= 0} />
        <AgentDot label="WS"
          active={connStatus === 'connected'}
        />
      </div>

      {/* Center Dashboard — agent status, commands, windows, conversations */}
      <CenterDashboard />
    </div>
  )
}
