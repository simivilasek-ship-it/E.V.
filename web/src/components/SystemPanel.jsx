import { useEffect } from 'react'
import { useJarvis } from '../store/jarvis'

function MetricBar({ value, warn = 70, danger = 90 }) {
  const color = value >= danger ? '#ff5252' : value >= warn ? '#fbbf24' : '#00d4ff'
  return (
    <div className="mt-1 h-1 rounded-full" style={{ background: '#1a3050' }}>
      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${value}%`, background: color }} />
    </div>
  )
}

function Metric({ label, value, unit = '%', warn, danger }) {
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs mb-1">
        <span style={{ color: '#4a6080' }}>{label}</span>
        <span style={{ color: '#00d4ff', fontFamily: 'Courier New' }}>{value}{unit}</span>
      </div>
      <MetricBar value={typeof value === 'number' ? value : 0} warn={warn} danger={danger} />
    </div>
  )
}

function LogLine({ log }) {
  const lvl = log.text.match(/ERROR|WARNING|WARN|INFO|DEBUG/)?.[0]?.toLowerCase() || 'info'
  const colors = { error: '#ff5252', warn: '#fbbf24', warning: '#fbbf24', info: '#7ea8d4', debug: '#4a6080' }
  return (
    <div className="text-xs py-0.5 border-b" style={{ color: colors[lvl] || '#7ea8d4', borderColor: '#0b1220' }}>
      {log.text.slice(0, 120)}
    </div>
  )
}

export default function SystemPanel() {
  const system    = useJarvis(s => s.system)
  const agents    = useJarvis(s => s.agents)
  const logs      = useJarvis(s => s.logs)
  const isConn    = useJarvis(s => s.isConnected)
  const fetchSys  = useJarvis(s => s.fetchSystem)
  const fetchAge  = useJarvis(s => s.fetchAgents)
  const clearLogs = useJarvis(s => s.clearLogs)

  useEffect(() => {
    fetchSys(); fetchAge()
    const t = setInterval(() => { fetchSys(); fetchAge() }, 3000)
    return () => clearInterval(t)
  }, [])

  const cpuVal  = typeof system.cpu  === 'number' ? Math.round(system.cpu)  : 0
  const ramVal  = typeof system.ram  === 'number' ? Math.round(system.ram)  : 0
  const diskVal = typeof system.disk === 'number' ? Math.round(system.disk) : 0

  return (
    <div className="flex flex-col gap-3 h-full" style={{ minHeight: 0 }}>
      {/* System metrics */}
      <div className="glass rounded-xl p-4">
        <div className="text-xs tracking-widest mb-3" style={{ color: '#4a6080' }}>SYSTÉM</div>
        <Metric label="CPU" value={cpuVal} warn={70} danger={90} />
        <Metric label="RAM" value={ramVal} warn={75} danger={90} />
        <Metric label="DISK" value={diskVal} warn={80} danger={95} />
        <div className="mt-2 flex items-center gap-2 text-xs">
          <div className="w-2 h-2 rounded-full" style={{ background: isConn ? '#00e676' : '#ff5252' }} />
          <span style={{ color: '#4a6080' }}>WebSocket {isConn ? 'připojen' : 'odpojeno'}</span>
        </div>
      </div>

      {/* Agents */}
      {agents.length > 0 && (
        <div className="glass rounded-xl p-4">
          <div className="text-xs tracking-widest mb-3" style={{ color: '#4a6080' }}>AGENTI</div>
          {agents.map((ag, i) => (
            <div key={i} className="flex justify-between text-xs mb-2">
              <span style={{ color: '#7ea8d4' }}>{ag.name || ag.type || 'agent'}</span>
              <span className="px-2 py-0.5 rounded text-xs"
                style={{ background: ag.running ? 'rgba(0,230,118,0.1)' : 'rgba(255,82,82,0.1)',
                         color: ag.running ? '#00e676' : '#ff5252' }}>
                {ag.running ? '● běží' : '○ stop'}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Logs */}
      <div className="glass rounded-xl p-4 flex-1" style={{ minHeight: 0 }}>
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs tracking-widest" style={{ color: '#4a6080' }}>LIVE LOGY</span>
          <button onClick={clearLogs} className="text-xs" style={{ color: '#4a6080' }}>clear</button>
        </div>
        <div className="overflow-y-auto" style={{ maxHeight: 220, minHeight: 80 }}>
          {logs.slice(-50).map((l, i) => <LogLine key={i} log={l} />)}
          {logs.length === 0 && (
            <div className="text-xs" style={{ color: '#4a6080' }}>Čeká na logy...</div>
          )}
        </div>
      </div>
    </div>
  )
}
