'use client'
import { useEffect, useRef, useState } from 'react'
import { useJarvis } from '@/store/jarvis'

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
      <div className="font-mono text-5xl font-bold tracking-tight"
        style={{ color: 'var(--cyan)', textShadow: '0 0 30px rgba(0,200,255,.35)' }}>
        {t}
      </div>
      <div className="font-mono text-sm mt-1 capitalize" style={{ color: 'var(--muted)' }}>{d}</div>
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
    <div className="flex flex-col items-center gap-1 px-4 py-3 rounded-xl"
      style={{ background: 'rgba(255,255,255,.03)', border: '1px solid rgba(255,255,255,.07)' }}>
      <div className="font-hud text-[8px] tracking-widest" style={{ color: 'var(--muted)' }}>{label}</div>
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
      className="flex items-center gap-2.5 px-4 py-3 rounded-xl text-sm font-medium transition-all text-left"
      style={{
        background: hover ? 'rgba(78,205,196,.1)' : 'rgba(255,255,255,.03)',
        border: `1px solid ${hover ? 'rgba(78,205,196,.3)' : 'rgba(255,255,255,.08)'}`,
        color: hover ? '#4ecdc4' : 'var(--text)',
        boxShadow: hover ? '0 0 16px rgba(78,205,196,.1)' : 'none',
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
        <div className="font-hud text-[9px] tracking-widest mb-3" style={{ color: 'var(--muted)' }}>
          RYCHLÉ AKCE
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
    </div>
  )
}
