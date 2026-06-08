'use client'
import { useState, useEffect, useRef, useCallback } from 'react'
import { useJarvis } from '@/store/jarvis'
import { apiUrl } from '@/lib/api'

// Ollama status widget
function OllamaStatus() {
  const [status, setStatus] = useState({ ollama: false, model: '—' })

  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch(apiUrl('/api/status'))
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

// Circular Gauge — plný kruh s animovaným dasharray
function CircularGauge({ value, max = 100, label, color, size = 80 }: {
  value: number; max?: number; label: string; color: string; size?: number
}) {
  const r    = (size / 2) - 8
  const circ = 2 * Math.PI * r
  const pct  = Math.min(value / max, 1)
  const dash = pct * circ

  // Dynamická barva dle zatížení
  const gaugeColor = value > 85 ? '#f43f5e' : value > 65 ? '#f59e0b' : color

  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:6 }}>
      <div style={{ position:'relative', width:size, height:size }}>
        <svg width={size} height={size} style={{ transform:'rotate(-90deg)' }}>
          {/* Track */}
          <circle cx={size/2} cy={size/2} r={r}
            fill="none" stroke="rgba(255,255,255,.06)" strokeWidth={6} />
          {/* Progress */}
          <circle cx={size/2} cy={size/2} r={r}
            fill="none" stroke={gaugeColor} strokeWidth={6}
            strokeLinecap="round"
            strokeDasharray={`${dash} ${circ}`}
            style={{
              filter:`drop-shadow(0 0 4px ${gaugeColor})`,
              transition:'stroke-dasharray 0.6s ease, stroke 0.3s ease',
            }}
          />
        </svg>
        {/* Center value */}
        <div style={{
          position:'absolute', inset:0,
          display:'flex', flexDirection:'column',
          alignItems:'center', justifyContent:'center',
        }}>
          <span style={{ fontFamily:'var(--font-mono)', fontSize:15, fontWeight:700, color:gaugeColor,
            transition:'color 0.3s ease', textShadow:`0 0 8px ${gaugeColor}` }}>
            {Math.round(value)}
          </span>
          <span style={{ fontFamily:'var(--font-mono)', fontSize:8, color:'var(--muted,var(--text2))' }}>%</span>
        </div>
      </div>
      <span style={{ fontFamily:'var(--font-hud)', fontSize:9, letterSpacing:'.12em', color:'var(--muted,var(--text2))' }}>
        {label}
      </span>
      {value > 85 && (
        <span style={{ fontFamily:'var(--font-hud)', fontSize:7, letterSpacing:'.1em', color:'#f43f5e', marginTop:-4 }}>
          HIGH
        </span>
      )}
      {value > 65 && value <= 85 && (
        <span style={{ fontFamily:'var(--font-hud)', fontSize:7, letterSpacing:'.1em', color:'#f59e0b', marginTop:-4 }}>
          WARN
        </span>
      )}
    </div>
  )
}

// Sparkline SVG — 60s history chart s gradient fill a glow dot
function Sparkline({ data, color, height = 36, width = '100%' }: {
  data: number[]; color: string; height?: number; width?: string | number
}) {
  const ref = useRef<HTMLDivElement>(null)
  const [w, setW] = useState(220)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    setW(el.clientWidth || 220)
    const ro = new ResizeObserver(() => setW(el.clientWidth || 220))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const gradId = `grad-${color.replace('#', '')}-${height}`

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
  const lastX   = w
  const lastY   = height - (data[data.length - 1] / max) * (height - 4) - 2

  return (
    <div ref={ref} style={{ width, position:'relative' }}>
      <svg width="100%" height={height} viewBox={`0 0 ${w} ${height}`}
        preserveAspectRatio="none" style={{ display:'block', overflow:'visible' }}>
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor={color} stopOpacity=".35"/>
            <stop offset="100%" stopColor={color} stopOpacity="0"/>
          </linearGradient>
        </defs>
        {/* Fill area */}
        <polygon points={fillPts} fill={`url(#${gradId})`} />
        {/* Line */}
        <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5"
          style={{ filter:`drop-shadow(0 0 3px ${color})` }} />
        {/* Live dot at current value */}
        <circle cx={lastX} cy={lastY} r="3" fill={color}
          style={{ filter:`drop-shadow(0 0 5px ${color})` }} />
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

interface SystemPanelProps { fullMode?: boolean; compact?: boolean }
export default function SystemPanel(_props: SystemPanelProps = {}) {
  const system   = useJarvis(s => s.system) as SystemData
  const agents   = useJarvis(s => s.agents) as unknown as Array<Record<string, unknown>>
  const logs     = useJarvis(s => s.logs) as Array<{ text?: string }>
  const isConn   = useJarvis(s => s.isConnected) as boolean
  const fetchAge = useJarvis(s => s.fetchAgents) as () => void
  const clearLogs= useJarvis(s => s.clearLogs) as () => void

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
          <CircularGauge value={cpu}  color="#00d4ff" label="CPU"  size={80} />
          <CircularGauge value={ram}  color="#0066ff" label="RAM"  size={80} />
          <CircularGauge value={disk} color="#8b5cf6" label="DISK" size={80} />
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
