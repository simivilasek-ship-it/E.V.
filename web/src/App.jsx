import { useEffect, useState } from 'react'
import { useJarvis } from './store/jarvis'
import AIOrb from './components/AIOrb'
import ChatPanel from './components/ChatPanel'
import SystemPanel from './components/SystemPanel'
import PluginStore from './components/PluginStore'
import ParticleBackground from './components/ParticleBackground'
import AgentGraph from './components/AgentGraph'
import ToastContainer from './components/Toast'

// Lucide-style inline SVG icons
const Icons = {
  chat:    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="nav-icon"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>,
  plugin:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="nav-icon"><path d="M20.24 12.24a6 6 0 00-8.49-8.49L5 10.5V19h8.5l6.74-6.76z"/><line x1="16" y1="8" x2="2" y2="22"/><line x1="17.5" y1="15" x2="9" y2="15"/></svg>,
  system:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="nav-icon"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>,
  agent:   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="nav-icon"><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>,
}

const TABS = [
  { id: 'CHAT',    label: 'CHAT',    icon: Icons.chat },
  { id: 'PLUGINY', label: 'PLUGINS', icon: Icons.plugin },
  { id: 'SYSTÉM',  label: 'SYSTEM',  icon: Icons.system },
  { id: 'AGENT',   label: 'AGENT',   icon: Icons.agent },
]

const STATE_GLOW = {
  idle:      'rgba(0,212,255,.15)',
  listening: 'rgba(0,212,255,.5)',
  thinking:  'rgba(139,92,246,.4)',
  speaking:  'rgba(0,229,160,.4)',
}

export default function App() {
  const connect        = useJarvis(s => s.connect)
  const connectMetrics = useJarvis(s => s.connectMetrics)
  const connectChat    = useJarvis(s => s.connectChat)
  const isConn         = useJarvis(s => s.isConnected)
  const connStatus     = useJarvis(s => s.connStatus)
  const connError      = useJarvis(s => s.connError)
  const retry          = useJarvis(s => s.retry)
  const orbState       = useJarvis(s => s.orbState)
  const [tab, setTab]  = useState('CHAT')

  useEffect(() => { connect(); connectMetrics(); connectChat() }, [])

  const connColor = { connected:'#00e5a0', connecting:'#ffb300', disconnected:'#ff3366', error:'#ff3366', failed:'#ff3366' }[connStatus] || '#4a6a8a'

  return (
    <div className="app">
      <ParticleBackground />
      {/* ── Top Bar ── */}
      <header className="topbar">
        <div style={{ display:'flex', alignItems:'center', gap:10, marginRight:24 }}>
          <div style={{
            width:34, height:34, borderRadius:8,
            border:`1.5px solid rgba(0,212,255,.5)`,
            display:'flex', alignItems:'center', justifyContent:'center',
            background:'rgba(0,212,255,.05)',
            boxShadow:'0 0 20px rgba(0,212,255,.2)',
            flexShrink:0,
          }}>
            <span style={{ fontFamily:'var(--font-hud)', fontSize:14, fontWeight:900, color:'var(--cyan)' }}>J</span>
          </div>
          <span className="logo-text">JARVIS</span>
          <span className="version-badge">v4.3</span>
        </div>

        <nav style={{ display:'flex', height:'100%', marginLeft:8 }}>
          {TABS.map(t => (
            <button key={t.id} className={`nav-tab ${tab===t.id?'active':''}`} onClick={() => setTab(t.id)}>
              {t.icon}
              {t.label}
            </button>
          ))}
        </nav>

        <div style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:16 }}>
          {/* Connection */}
          <button onClick={retry} className="conn-badge" style={{
            color: connColor,
            borderColor: `${connColor}33`,
            background: `${connColor}0a`,
          }}>
            <span style={{
              width:6, height:6, borderRadius:'50%',
              background: connColor,
              boxShadow: isConn ? `0 0 8px ${connColor}` : 'none',
              display:'block', flexShrink:0,
              animation: connStatus==='connecting' ? 'pulse 1s ease-in-out infinite' : 'none',
            }} />
            {connStatus.toUpperCase()}
          </button>

          {/* Orb state */}
          <div style={{
            fontFamily:'var(--font-hud)', fontSize:9, letterSpacing:'.15em',
            color: { idle:'var(--text2)', listening:'var(--cyan)', thinking:'var(--purple)', speaking:'var(--green)' }[orbState],
            textShadow: orbState!=='idle' ? `0 0 10px currentColor` : 'none',
            transition:'all .5s',
          }}>
            {{ idle:'○ IDLE', listening:'◉ LISTENING', thinking:'◎ PROCESSING', speaking:'● SPEAKING' }[orbState]}
          </div>
        </div>
      </header>

      {/* Error banner */}
      {connError && (
        <div style={{
          background:'rgba(255,51,102,.06)', borderBottom:'1px solid rgba(255,51,102,.2)',
          padding:'7px 24px', display:'flex', alignItems:'center', gap:12, fontSize:11,
          fontFamily:'var(--font-mono)',
        }}>
          <span style={{ color:'var(--red)', fontSize:14 }}>⚠</span>
          <span style={{ color:'rgba(255,100,130,.9)', flex:1 }}>{connError}</span>
          <button onClick={retry} style={{
            padding:'3px 14px', borderRadius:4, fontSize:10, cursor:'pointer',
            background:'rgba(255,51,102,.12)', color:'var(--red)',
            border:'1px solid rgba(255,51,102,.3)',
            fontFamily:'var(--font-hud)', letterSpacing:'.1em',
          }}>RETRY</button>
        </div>
      )}

      {/* ── Main ── */}
      <main style={{ overflow:'hidden', height:'100%' }}>
        {tab === 'CHAT' && (
          <div className="main-grid">
            <div className="panel chat-panel">
              <ChatPanel />
            </div>

            <div className="orb-col" style={{ alignItems:'center' }}>
              <div className="panel orb-panel" style={{
                borderColor:'rgba(0,212,255,.18)',
                width:'100%',
                boxShadow:`0 0 30px ${STATE_GLOW[orbState]}, inset 0 0 30px rgba(0,212,255,.03)`,
                transition:'box-shadow 1.2s ease',
              }}>
                <style>{`
                  @keyframes orbGlow {
                    0%,100% { box-shadow: 0 0 30px ${STATE_GLOW[orbState]}, 0 0 60px ${STATE_GLOW[orbState]}55; }
                    50%     { box-shadow: 0 0 60px ${STATE_GLOW[orbState]}, 0 0 120px ${STATE_GLOW[orbState]}88; }
                  }
                `}</style>
                <div style={{
                  borderRadius:'50%',
                  animation: orbState !== 'idle' ? 'orbGlow 1.5s ease-in-out infinite' : 'none',
                  transition:'all 1s ease',
                }}>
                  <AIOrb size={280} />
                </div>
              </div>

              {/* Shortcuts */}
              <div className="panel" style={{ padding:'12px 14px', flexShrink:0 }}>
                <div className="panel-title" style={{ marginBottom:10 }}>SHORTCUTS</div>
                {[['ENTER','Send'],['SHIFT+ENTER','New line'],['↑ ↓','History']].map(([k,v]) => (
                  <div key={k} style={{ display:'flex', justifyContent:'space-between', fontSize:11, marginBottom:7 }}>
                    <span style={{ fontFamily:'var(--font-mono)', color:'var(--text2)', fontSize:10 }}>{k}</span>
                    <span style={{ color:'#4a6a8a' }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="sys-col">
              <SystemPanel />
            </div>
          </div>
        )}

        {tab === 'PLUGINY' && (
          <div style={{ padding:12, maxWidth:680 }}>
            <div className="panel" style={{ padding:20 }}>
              <PluginStore />
            </div>
          </div>
        )}

        {tab === 'SYSTÉM' && (
          <div style={{ padding:12, maxWidth:500, height:'100%' }}>
            <div className="sys-col" style={{ height:'100%' }}>
              <SystemPanel fullMode />
            </div>
          </div>
        )}

        {tab === 'AGENT' && (
          <div style={{ padding:12, maxWidth:900, height:'100%', overflowY:'auto' }}>
            <div className="panel" style={{ padding:0 }}>
              <AgentGraph active={tab === 'AGENT'} />
            </div>
          </div>
        )}
      </main>
      <ToastContainer />
    </div>
  )
}
