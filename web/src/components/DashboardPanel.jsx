import { useEffect, useState, useCallback } from 'react'
import { useJarvis } from '../store/jarvis'

const API = 'http://localhost:8002'

const S = {
  card:  { background:'#0b1220', border:'1px solid #1a3050', borderRadius:8, padding:'14px 16px', marginBottom:12 },
  title: { color:'#475569', fontSize:9, letterSpacing:'0.15em', textTransform:'uppercase', marginBottom:10 },
  badge: (ok) => ({
    display:'inline-block', padding:'2px 8px', borderRadius:3, fontSize:10,
    background: ok ? '#064e3b' : '#7f1d1d',
    color:      ok ? '#10b981' : '#ef4444',
  }),
  bar: (v) => {
    const color = v > 90 ? '#ef4444' : v > 70 ? '#fbbf24' : '#00d4ff'
    return { width:`${v}%`, height:'100%', background:color, borderRadius:2, transition:'width .5s' }
  },
  row: { display:'flex', justifyContent:'space-between', alignItems:'center', padding:'5px 0', borderBottom:'1px solid #0b1220', fontSize:12 },
}

function MetricCard({ label, value, color='#00d4ff' }) {
  return (
    <div style={{ background:'#0b1220', border:'1px solid #1a3050', borderRadius:8, padding:'12px 14px', flex:1 }}>
      <div style={S.title}>{label}</div>
      <div style={{ fontSize:26, fontWeight:700, color, fontFamily:'var(--font-hud,monospace)' }}>{value}%</div>
      <div style={{ height:3, background:'#1a3050', borderRadius:2, marginTop:6 }}>
        <div style={S.bar(Number(value))} />
      </div>
    </div>
  )
}

export default function DashboardPanel() {
  const system  = useJarvis(s => s.system)
  const logs    = useJarvis(s => s.logs)
  const agents  = useJarvis(s => s.agents)

  const [audit,     setAudit]     = useState([])
  const [scheduler, setScheduler] = useState([])
  const [ollama,    setOllama]    = useState({ ok: false, model: '—' })
  const [uptime,    setUptime]    = useState('—')

  const refresh = useCallback(async () => {
    try {
      const [st, au, sc] = await Promise.all([
        fetch(`${API}/api/status`).then(r => r.json()).catch(() => ({})),
        fetch(`${API}/api/audit`).then(r => r.json()).catch(() => []),
        fetch(`${API}/api/scheduler`).then(r => r.json()).catch(() => []),
      ])
      setOllama({ ok: st.ollama, model: st.model || '—' })
      setAudit(Array.isArray(au) ? au.slice(-20).reverse() : [])
      setScheduler(Array.isArray(sc) ? sc : [])
    } catch {}
  }, [])

  useEffect(() => {
    refresh()
    const iv = setInterval(refresh, 6000)
    return () => clearInterval(iv)
  }, [refresh])

  // Uptime počítadlo
  useEffect(() => {
    const start = Date.now()
    const iv = setInterval(() => {
      const s = Math.floor((Date.now() - start) / 1000)
      const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
      setUptime(`${h > 0 ? h + 'h ' : ''}${m}m ${sec}s`)
    }, 1000)
    return () => clearInterval(iv)
  }, [])

  return (
    <div style={{ height:'100%', overflowY:'auto', padding:14, fontFamily:'var(--font-mono,monospace)' }}>

      {/* Metriky */}
      <div style={S.title}>SYSTÉMOVÉ METRIKY</div>
      <div style={{ display:'flex', gap:10, marginBottom:14 }}>
        <MetricCard label="CPU" value={system.cpu || 0} />
        <MetricCard label="RAM" value={system.ram || 0} color="#a78bfa" />
        <MetricCard label="DISK" value={system.disk || 0} color="#34d399" />
        <div style={{ background:'#0b1220', border:'1px solid #1a3050', borderRadius:8, padding:'12px 14px', flex:1 }}>
          <div style={S.title}>OLLAMA</div>
          <div style={{ display:'flex', alignItems:'center', gap:6 }}>
            <span style={{ width:7, height:7, borderRadius:'50%', background: ollama.ok ? '#10b981':'#ef4444', display:'inline-block', flexShrink:0 }} />
            <span style={{ fontSize:12, color: ollama.ok ? '#10b981':'#ef4444' }}>{ollama.ok ? 'Online' : 'Offline'}</span>
          </div>
          <div style={{ fontSize:10, color:'#475569', marginTop:4 }}>{ollama.model}</div>
          <div style={{ fontSize:10, color:'#1a3050', marginTop:2 }}>uptime {uptime}</div>
        </div>
      </div>

      {/* Agenti */}
      <div style={S.card}>
        <div style={S.title}>BACKGROUND AGENTI</div>
        {Array.isArray(agents) && agents.length > 0 ? (
          agents.map((ag, i) => (
            <div key={i} style={S.row}>
              <span style={{ color:'#e2f0ff' }}>{ag.name || ag}</span>
              <span style={S.badge(ag.running !== false)}>
                {ag.running !== false ? 'běží' : 'zastaven'}
              </span>
            </div>
          ))
        ) : (
          <div style={{ display:'flex', gap:16 }}>
            {['cpu_monitor','ram_monitor','disk_monitor'].map(n => (
              <div key={n} style={S.row}>
                <span style={{ color:'#7ea8d4', fontSize:11 }}>{n}</span>
                <span style={{ ...S.badge(true), marginLeft:8 }}>běží</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Scheduler */}
      <div style={S.card}>
        <div style={S.title}>NAPLÁNOVANÉ ÚLOHY</div>
        {scheduler.length > 0 ? (
          <table style={{ width:'100%', borderCollapse:'collapse', fontSize:11 }}>
            <thead>
              <tr style={{ color:'#475569', fontSize:9, letterSpacing:'.1em' }}>
                <th style={{ textAlign:'left', padding:'4px 6px', borderBottom:'1px solid #1a3050' }}>NÁZEV</th>
                <th style={{ textAlign:'left', padding:'4px 6px', borderBottom:'1px solid #1a3050' }}>SPUŠTĚNÍ</th>
                <th style={{ textAlign:'left', padding:'4px 6px', borderBottom:'1px solid #1a3050' }}>OPAKOVÁNÍ</th>
                <th style={{ textAlign:'right', padding:'4px 6px', borderBottom:'1px solid #1a3050' }}>POČET</th>
              </tr>
            </thead>
            <tbody>
              {scheduler.map((t, i) => (
                <tr key={i}>
                  <td style={{ padding:'5px 6px', color:'#e2f0ff', borderBottom:'1px solid #0b1220' }}>{t.name}</td>
                  <td style={{ padding:'5px 6px', color:'#7ea8d4', borderBottom:'1px solid #0b1220' }}>{t.fire_at}</td>
                  <td style={{ padding:'5px 6px', color:'#475569', borderBottom:'1px solid #0b1220' }}>{t.repeat}</td>
                  <td style={{ padding:'5px 6px', color:'#475569', textAlign:'right', borderBottom:'1px solid #0b1220' }}>{t.run_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ color:'#2d3748', fontSize:11 }}>Žádné naplánované úlohy</div>
        )}
      </div>

      {/* Audit log */}
      <div style={S.card}>
        <div style={S.title}>AUDIT LOG (posledních 20)</div>
        <table style={{ width:'100%', borderCollapse:'collapse', fontSize:11 }}>
          <thead>
            <tr style={{ color:'#475569', fontSize:9, letterSpacing:'.1em' }}>
              <th style={{ textAlign:'left', padding:'4px 6px', borderBottom:'1px solid #1a3050' }}>ČAS</th>
              <th style={{ textAlign:'left', padding:'4px 6px', borderBottom:'1px solid #1a3050' }}>AKCE</th>
              <th style={{ textAlign:'left', padding:'4px 6px', borderBottom:'1px solid #1a3050' }}>POVOLENO</th>
              <th style={{ textAlign:'left', padding:'4px 6px', borderBottom:'1px solid #1a3050' }}>DŮVOD</th>
            </tr>
          </thead>
          <tbody>
            {audit.length > 0 ? audit.map((e, i) => {
              const t = e.timestamp ? new Date(e.timestamp * 1000).toLocaleTimeString() : '—'
              return (
                <tr key={i}>
                  <td style={{ padding:'4px 6px', color:'#475569', borderBottom:'1px solid #0b1220', whiteSpace:'nowrap' }}>{t}</td>
                  <td style={{ padding:'4px 6px', color:'#e2f0ff', borderBottom:'1px solid #0b1220' }}>{e.action}</td>
                  <td style={{ padding:'4px 6px', borderBottom:'1px solid #0b1220' }}>
                    <span style={S.badge(e.allowed)}>{e.allowed ? 'ANO' : 'NE'}</span>
                  </td>
                  <td style={{ padding:'4px 6px', color:'#475569', borderBottom:'1px solid #0b1220', fontSize:10 }}>{e.reason}</td>
                </tr>
              )
            }) : (
              <tr><td colSpan={4} style={{ padding:'8px 6px', color:'#2d3748' }}>Prázdný audit log</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* System logy */}
      <div style={S.card}>
        <div style={S.title}>SYSTEM LOGY (posledních 100)</div>
        <div style={{ background:'#050a15', borderRadius:4, padding:'8px 10px', height:200, overflowY:'auto', fontSize:10, lineHeight:1.7 }}>
          {logs.length === 0
            ? <span style={{ color:'#1a3050' }}>Připojuji se na WebSocket…</span>
            : logs.slice(-100).reverse().map((l, i) => (
                <div key={i} style={{ color: l.text?.includes('ERROR') ? '#ef4444' : l.text?.includes('WARN') ? '#fbbf24' : '#7ea8d4', borderBottom:'1px solid #0b1220', paddingBottom:1 }}>
                  {l.text}
                </div>
              ))
          }
        </div>
      </div>

    </div>
  )
}
