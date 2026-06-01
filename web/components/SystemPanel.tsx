'use client'
import { useState, useEffect, useRef, useCallback } from 'react'
import { useJarvis } from '@/store/jarvis'

// Ollama status widget
function OllamaStatus() {
  const [status, setStatus] = useState({ ollama: false, model: '—' })

  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch('http://localhost:8002/api/status')
        const d = await r.json()
        setStatus(d)
      } catch {}
    }
    check()
    const t = setInterval(check, 10000)
    return () => clearInterval(t)
  }, [])

  return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between',
      padding:'8px 14px', borderBottom:'1px solid var(--border)', flexShrink:0 }}>
      <span style={{ fontFamily:'var(--font-hud)', fontSize:8, letterSpacing:'.15em', color:'var(--text2)' }}>
        OLLAMA
      </span>
      <div style={{ display:'flex', alignItems:'center', gap:6 }}>
        <span style={{ fontFamily:'var(--font-mono)', fontSize:10,
          color: status.ollama ? 'var(--green)' : 'var(--red)' }}>
          {status.ollama ? '● ONLINE' : '○ OFFLINE'}
        </span>
        {status.model && (
          <span style={{ fontFamily:'var(--font-mono)', fontSize:9,
            color:'var(--text2)', padding:'1px 6px',
            border:'1px solid var(--border)', borderRadius:3 }}>
            {status.model}
          </span>
        )}
      </div>
    </div>
  )
}

// SVG Arc Progress Ring
function ArcRing({ value, color, label, size = 72 }: { value: number; color: string; label: string; size?: number }) {
  const r    = 28
  const cx   = size / 2
  const cy   = size / 2
  const circ = 2 * Math.PI * r
  // Arc from -220° to 40° (240° sweep)
  const sweep   = 240
  const startDeg = 150
  const pct     = Math.min(Math.max(value, 0), 100) / 100
  const dashArr = circ
  const dashOff = circ * (1 - (pct * sweep / 360))

  const warningCol = value >= 90 ? '#ff3366' : value >= 70 ? '#ffb300' : color

  // Convert degrees to radians for arc endpoints
  const toRad = (d: number) => (d - 90) * Math.PI / 180
  const startR = toRad(startDeg)
  const endR   = toRad(startDeg + sweep)
  const trackD = `M ${cx + r * Math.cos(startR)} ${cy + r * Math.sin(startR)} A ${r} ${r} 0 1 1 ${cx + r * Math.cos(endR)} ${cy + r * Math.sin(endR)}`

  const valueR  = toRad(startDeg + pct * sweep)
  const valueD  = `M ${cx + r * Math.cos(startR)} ${cy + r * Math.sin(startR)} A ${r} ${r} 0 ${pct * sweep > 180 ? 1 : 0} 1 ${cx + r * Math.cos(valueR)} ${cy + r * Math.sin(valueR)}`

  return (
    <div className="arc-wrap">
      <svg width={size} height={size} style={{ overflow:'visible' }}>
        {/* Background track */}
        <path d={trackD} fill="none" stroke="rgba(255,255,255,.06)" strokeWidth="4"
          strokeLinecap="round" />
        {/* Value arc */}
        <path d={valueD} fill="none" stroke={warningCol} strokeWidth="4"
          strokeLinecap="round"
          style={{ filter:`drop-shadow(0 0 4px ${warningCol})`, transition:'all .6s ease' }} />
        {/* Glow dot at end */}
        {value > 2 && (
          <circle
            cx={cx + r * Math.cos(valueR)}
            cy={cy + r * Math.sin(valueR)}
            r="4"
            fill={warningCol}
            style={{ filter:`drop-shadow(0 0 6px ${warningCol})` }}
          />
        )}
        {/* Center value */}
        <text x={cx} y={cy + 2} textAnchor="middle" dominantBaseline="middle"
          style={{ fontFamily:'var(--font-mono)', fontSize:14, fill: warningCol,
                   filter:`drop-shadow(0 0 4px ${warningCol})` }}>
          {value}
        </text>
        <text x={cx} y={cy + 16} textAnchor="middle" dominantBaseline="middle"
          style={{ fontFamily:'var(--font-hud)', fontSize:7, fill:'var(--text2)', letterSpacing:'.1em' }}>
          %
        </text>
      </svg>
      <div className="arc-label">{label}</div>
      {value >= 90 && <div style={{fontFamily:'var(--font-hud)',fontSize:7,color:'var(--red)',letterSpacing:'.1em',textAlign:'center'}}>HIGH</div>}
      {value >= 70 && value < 90 && <div style={{fontFamily:'var(--font-hud)',fontSize:7,color:'var(--amber)',letterSpacing:'.1em',textAlign:'center'}}>WARN</div>}
    </div>
  )
}

// Sparkline SVG
function Sparkline({ data, color, height = 36, width = '100%' }: { data: number[]; color: string; height?: number; width?: string | number }) {
  const ref = useRef<HTMLDivElement>(null)
  const [w, setW] = useState(220)

  useEffect(() => {
    if (ref.current) setW(ref.current.clientWidth || 220)
  }, [])

  if (!data || data.length < 2) return (
    <div ref={ref} style={{ height, opacity:.3, display:'flex', alignItems:'center',
      fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text2)' }}>
      collecting...
    </div>
  )

  const max = Math.max(...data, 1)
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w
    const y = height - (v / max) * (height - 4) - 2
    return `${x},${y}`
  }).join(' ')

  const fillPts = `0,${height} ${pts} ${w},${height}`

  return (
    <div ref={ref} style={{ width, position:'relative' }}>
      <svg width="100%" height={height} preserveAspectRatio="none" style={{ display:'block' }}>
        <defs>
          <linearGradient id={`grad-${color.replace('#','')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity=".35"/>
            <stop offset="100%" stopColor={color} stopOpacity="0"/>
          </linearGradient>
        </defs>
        <polygon points={fillPts} fill={`url(#grad-${color.replace('#','')})`} />
        <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5"
          style={{ filter:`drop-shadow(0 0 3px ${color})` }} />
        {/* Last value dot */}
        {data.length > 0 && (() => {
          const lx = w
          const ly = height - (data[data.length-1] / max) * (height - 4) - 2
          return <circle cx={lx} cy={ly} r="3" fill={color}
            style={{ filter:`drop-shadow(0 0 5px ${color})` }} />
        })()}
      </svg>
    </div>
  )
}

interface SystemData {
  cpu?: number
  ram?: number
  disk?: number
  cpu_temp?: number | null
  net?: { recv: number; sent: number } | null
  gpu?: { usage?: number; name?: string } | null
}

function AdvancedMetrics({ system }: { system: SystemData }) {
  const hasCpuTemp = system.cpu_temp != null
  const hasNet     = system.net != null
  const hasGpu     = system.gpu?.usage != null

  if (!hasCpuTemp && !hasNet && !hasGpu) return null

  return (
    <div className="panel" style={{ padding:'10px 14px' }}>
      <div className="panel-title" style={{ marginBottom:10 }}>ADVANCED</div>

      {hasCpuTemp && (
        <div style={{ display:'flex', justifyContent:'space-between', marginBottom:8 }}>
          <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text2)' }}>CPU TEMP</span>
          <span style={{ fontFamily:'var(--font-mono)', fontSize:12,
            color: (system.cpu_temp ?? 0) > 80 ? 'var(--red)' : (system.cpu_temp ?? 0) > 70 ? 'var(--amber)' : 'var(--cyan)' }}>
            {system.cpu_temp}°C
          </span>
        </div>
      )}

      {hasNet && system.net && (
        <div style={{ marginBottom:8 }}>
          <div style={{ display:'flex', justifyContent:'space-between', marginBottom:2 }}>
            <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text2)' }}>NETWORK</span>
          </div>
          <div style={{ display:'flex', gap:12 }}>
            <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--green)' }}>
              ↓ {system.net.recv} KB/s
            </span>
            <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--cyan)' }}>
              ↑ {system.net.sent} KB/s
            </span>
          </div>
        </div>
      )}

      {hasGpu && system.gpu && (
        <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
          <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text2)' }}>
            GPU {system.gpu.name ? `(${system.gpu.name.slice(0,12)})` : ''}
          </span>
          <span style={{ fontFamily:'var(--font-mono)', fontSize:12, color:'var(--purple)' }}>
            {system.gpu.usage}%
          </span>
        </div>
      )}
    </div>
  )
}

const MAX_HISTORY = 60

const LOG_PATTERNS: Array<{ re: RegExp; color: string }> = [
  { re: /ERROR|CRITICAL/i, color: 'var(--red)' },
  { re: /WARN/i,           color: 'var(--amber)' },
  { re: /✓|OK|SUCCESS/i,  color: 'var(--green)' },
  { re: /INFO/i,           color: 'var(--text2)' },
]
function logColor(text: string) {
  for (const {re, color} of LOG_PATTERNS) {
    if (re.test(text)) return color
  }
  return 'var(--text2)'
}

export default function SystemPanel() {
  const system   = useJarvis((s: Record<string, unknown>) => s.system) as SystemData
  const agents   = useJarvis((s: Record<string, unknown>) => s.agents) as Array<Record<string, unknown>>
  const logs     = useJarvis((s: Record<string, unknown>) => s.logs) as Array<{ text?: string }>
  const isConn   = useJarvis((s: Record<string, unknown>) => s.isConnected) as boolean
  const fetchAge = useJarvis((s: Record<string, unknown>) => s.fetchAgents) as () => void
  const clearLogs= useJarvis((s: Record<string, unknown>) => s.clearLogs) as () => void

  const [cpuHist,  setCpuHist]  = useState<number[]>([])
  const [ramHist,  setRamHist]  = useState<number[]>([])
  const [diskHist, setDiskHist] = useState<number[]>([])

  useEffect(() => {
    fetchAge()
    const t = setInterval(fetchAge, 5000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    setCpuHist(h  => [...h.slice(-(MAX_HISTORY-1)),  Math.round(system.cpu  || 0)])
    setRamHist(h  => [...h.slice(-(MAX_HISTORY-1)),  Math.round(system.ram  || 0)])
    setDiskHist(h => [...h.slice(-(MAX_HISTORY-1)),  Math.round(system.disk || 0)])
  }, [system.cpu, system.ram, system.disk])

  const cpu  = Math.round(system.cpu  || 0)
  const ram  = Math.round(system.ram  || 0)
  const disk = Math.round(system.disk || 0)

  return (
    <>
      {/* Arc metrics */}
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">SYSTEM METRICS</span>
          <span style={{ fontFamily:'var(--font-mono)', fontSize:9, color: isConn ? 'var(--green)' : 'var(--red)' }}>
            {isConn ? '● LIVE' : '○ OFFLINE'}
          </span>
        </div>
        <OllamaStatus />
        <div className="arc-row" style={{ padding:'16px 12px 12px' }}>
          <ArcRing value={cpu}  color="#00d4ff" label="CPU"  />
          <ArcRing value={ram}  color="#0066ff" label="RAM"  />
          <ArcRing value={disk} color="#8b5cf6" label="DISK" />
        </div>
      </div>

      {/* Sparklines */}
      <div className="panel" style={{ padding:'12px 14px' }}>
        <div style={{ marginBottom:12 }}>
          <div style={{ display:'flex', justifyContent:'space-between', marginBottom:6 }}>
            <span className="arc-label">CPU HISTORY (60s)</span>
            <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--cyan)' }}>{cpu}%</span>
          </div>
          <Sparkline data={cpuHist} color="#00d4ff" height={32} />
        </div>
        <div style={{ marginBottom:12 }}>
          <div style={{ display:'flex', justifyContent:'space-between', marginBottom:6 }}>
            <span className="arc-label">RAM HISTORY (60s)</span>
            <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'#0066ff' }}>{ram}%</span>
          </div>
          <Sparkline data={ramHist} color="#0066ff" height={32} />
        </div>
        <div style={{ marginTop:10 }}>
          <div style={{ display:'flex', justifyContent:'space-between', marginBottom:6 }}>
            <span className="arc-label">DISK USAGE</span>
            <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--purple)' }}>{disk}%</span>
          </div>
          <Sparkline data={diskHist} color="#8b5cf6" height={24} />
        </div>
      </div>

      {/* Advanced metrics */}
      <AdvancedMetrics system={system} />

      {/* Agents */}
      {Array.isArray(agents) && agents.length > 0 && (
        <div className="panel" style={{ padding:'12px 14px', flexShrink:0 }}>
          <div className="panel-title" style={{ marginBottom:10 }}>AGENTS</div>
          {agents.map((ag, i) => (
            <div key={i} style={{ display:'flex', justifyContent:'space-between', marginBottom:8 }}>
              <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text2)' }}>
                {(ag.name as string) || (ag.type as string) || `agent_${i}`}
              </span>
              <span style={{ fontFamily:'var(--font-mono)', fontSize:9, padding:'2px 8px', borderRadius:10,
                background: ag.running ? 'rgba(0,229,160,.1)' : 'rgba(255,51,102,.1)',
                color: ag.running ? 'var(--green)' : 'var(--red)',
                border:`1px solid ${ag.running ? 'rgba(0,229,160,.2)' : 'rgba(255,51,102,.2)'}` }}>
                {ag.running ? '● ON' : '○ OFF'}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Live logs */}
      <div className="panel log-panel">
        <div className="panel-header">
          <span className="panel-title">LIVE LOG</span>
          <button onClick={clearLogs} style={{
            fontFamily:'var(--font-hud)', fontSize:8, letterSpacing:'.1em',
            color:'var(--text2)', background:'none', border:'none', cursor:'pointer',
          }}>CLEAR</button>
        </div>
        <div className="log-box">
          {logs.slice(-80).map((l, i) => {
            const t = l.text || ''
            return (
              <div key={i} className="log-line" style={{ color: logColor(t) }}>
                {t.slice(0, 110)}
              </div>
            )
          })}
          {logs.length === 0 && (
            <div style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text2)', opacity:.5 }}>
              awaiting data...
            </div>
          )}
        </div>
      </div>
    </>
  )
}
