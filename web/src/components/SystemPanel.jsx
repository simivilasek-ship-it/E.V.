import { useEffect } from 'react'
import { useJarvis } from '../store/jarvis'

function Bar({ value, warn=70, danger=90 }) {
  const color = value>=danger ? '#ef4444' : value>=warn ? '#fbbf24' : '#00d4ff'
  return (
    <div className="bar">
      <div className="bar-fill" style={{ width:`${value}%`, background:color }} />
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

  const cpu  = Math.round(system.cpu  || 0)
  const ram  = Math.round(system.ram  || 0)
  const disk = Math.round(system.disk || 0)

  return (
    <>
      {/* Metrics */}
      <div className="panel" style={{ padding:'14px 16px' }}>
        <div style={{ fontSize:10, letterSpacing:'.12em', color:'#3a5a78', marginBottom:14 }}>SYSTÉM</div>
        {[['CPU', cpu, 70, 90],['RAM', ram, 75, 90],['DISK', disk, 80, 95]].map(([l,v,w,d]) => (
          <div key={l} className="metric-row">
            <div className="metric-label">
              <span style={{ color:'#6080a0', fontSize:11 }}>{l}</span>
              <span style={{ color:'#00d4ff', fontSize:12, fontFamily:'Courier New' }}>{v}%</span>
            </div>
            <Bar value={v} warn={w} danger={d} />
          </div>
        ))}
        <div style={{ marginTop:12, display:'flex', alignItems:'center', gap:6, fontSize:11 }}>
          <div style={{ width:6, height:6, borderRadius:'50%',
            background: isConn ? '#00e676' : '#ef4444',
            boxShadow: isConn ? '0 0 6px #00e676' : 'none' }} />
          <span style={{ color:'#3a5a78' }}>WebSocket {isConn ? 'connected' : 'offline'}</span>
        </div>
      </div>

      {/* Agents */}
      {Array.isArray(agents) && agents.length > 0 && (
        <div className="panel" style={{ padding:'14px 16px' }}>
          <div style={{ fontSize:10, letterSpacing:'.12em', color:'#3a5a78', marginBottom:10 }}>AGENTI</div>
          {agents.map((ag, i) => (
            <div key={i} style={{ display:'flex', justifyContent:'space-between', marginBottom:8, alignItems:'center' }}>
              <span style={{ color:'#8090b0', fontSize:11 }}>{ag.name || ag.type || 'agent'}</span>
              <span style={{ fontSize:10, padding:'2px 7px', borderRadius:10,
                background: ag.running ? 'rgba(0,230,118,.1)' : 'rgba(239,68,68,.1)',
                color: ag.running ? '#00e676' : '#ef4444',
                border: `1px solid ${ag.running ? 'rgba(0,230,118,.2)' : 'rgba(239,68,68,.2)'}` }}>
                {ag.running ? '● on' : '○ off'}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Logs */}
      <div className="panel" style={{ display:'flex', flexDirection:'column', flex:1, minHeight:0, overflow:'hidden' }}>
        <div style={{ display:'flex', justifyContent:'space-between', padding:'12px 14px 8px',
          borderBottom:'1px solid rgba(0,212,255,.06)', flexShrink:0 }}>
          <span style={{ fontSize:10, letterSpacing:'.12em', color:'#3a5a78' }}>LIVE LOGY</span>
          <button onClick={clearLogs} style={{ fontSize:10, color:'#3a5a78', cursor:'pointer', background:'none', border:'none' }}>clear</button>
        </div>
        <div className="log-box">
          {logs.slice(-60).map((l,i) => {
            const lvl = l.text.match(/ERROR|WARNING|WARN/)?.[0]?.toLowerCase()
            const cls = lvl==='error' ? 'log-error' : lvl==='warning'||lvl==='warn' ? 'log-warn' : 'log-info'
            return <div key={i} className={`log-line ${cls}`}>{l.text.slice(0,100)}</div>
          })}
          {logs.length===0 && <div style={{ color:'#3a5a78', fontSize:11 }}>Čeká na logy...</div>}
        </div>
      </div>
    </>
  )
}
