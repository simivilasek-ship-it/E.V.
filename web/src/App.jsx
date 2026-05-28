import { useEffect, useState } from 'react'
import { useJarvis } from './store/jarvis'
import AIOrb from './components/AIOrb'
import ChatPanel from './components/ChatPanel'
import SystemPanel from './components/SystemPanel'
import PluginStore from './components/PluginStore'

const TABS = ['CHAT', 'PLUGINY', 'SYSTÉM']

const STATE_COLORS = {
  idle:'#3a5a78', listening:'#00d4ff', thinking:'#8b5cf6', speaking:'#00e676',
}

export default function App() {
  const connect  = useJarvis(s => s.connect)
  const isConn   = useJarvis(s => s.isConnected)
  const connStatus = useJarvis(s => s.connStatus)
  const orbState = useJarvis(s => s.orbState)
  const [tab, setTab] = useState('CHAT')

  const connectMetrics = useJarvis(s => s.connectMetrics)
  useEffect(() => { connect(); connectMetrics() }, [])

  const connColor = { connected:'#00e676', connecting:'#fbbf24', disconnected:'#ef4444', error:'#ef4444' }[connStatus] || '#3a5a78'

  return (
    <div className="app">
      {/* Top bar */}
      <header className="topbar">
        {/* Logo */}
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <div style={{
            width:32, height:32, borderRadius:'50%',
            border:`1.5px solid rgba(0,212,255,.5)`,
            display:'flex', alignItems:'center', justifyContent:'center',
            fontSize:13, color:'#00d4ff',
            boxShadow:'0 0 16px rgba(0,212,255,.25)',
            flexShrink: 0,
          }}>J</div>
          <span style={{ color:'#00d4ff', letterSpacing:'.22em', fontSize:14,
                         textShadow:'0 0 20px rgba(0,212,255,.7)' }}>JARVIS</span>
          <span style={{ fontSize:10, color:'#3a5a78', padding:'2px 8px',
                         border:'1px solid #1a3050', borderRadius:20 }}>v4.3</span>
        </div>

        {/* Tabs */}
        <nav style={{ display:'flex', gap:4, marginLeft:16 }}>
          {TABS.map(t => (
            <button key={t} className={`nav-tab ${tab===t?'active':''}`} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </nav>

        {/* Right status */}
        <div style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:12 }}>
          <div style={{ display:'flex', alignItems:'center', gap:5, fontSize:11 }}>
            <div style={{
              width:6, height:6, borderRadius:'50%',
              background: connColor,
              boxShadow: isConn ? `0 0 8px ${connColor}` : 'none',
              transition:'all .5s',
            }} />
            <span style={{ color:'#3a5a78' }}>{connStatus}</span>
          </div>
          <div style={{ fontSize:11, color: STATE_COLORS[orbState], transition:'color .5s' }}>
            {{ idle:'○ idle', listening:'◉ listening', thinking:'◎ thinking', speaking:'● speaking' }[orbState]}
          </div>
        </div>
      </header>

      {/* Main */}
      <main style={{ overflow:'hidden', height:'100%' }}>
        {tab === 'CHAT' && (
          <div className="main-grid">
            {/* Chat */}
            <div className="panel chat-panel" style={{ overflow:'hidden' }}>
              <ChatPanel />
            </div>

            {/* Orb column */}
            <div className="orb-col">
              <div className="panel orb-panel glow-cyan" style={{
                border: `1px solid rgba(0,212,255,.18)`,
                boxShadow: `0 0 40px rgba(0,212,255,.07), 0 0 80px rgba(0,212,255,.03)`,
              }}>
                <AIOrb size={280} />
                <div style={{ width:'100%', marginTop:16, borderTop:'1px solid rgba(0,212,255,.08)', paddingTop:12 }}>
                  <div style={{ fontSize:10, color:'#3a5a78', letterSpacing:'.1em', marginBottom:8 }}>ZKRATKY</div>
                  {[['Enter','odeslat'],['Shift+Enter','nový řádek'],['↑ ↓','historie']].map(([k,v]) => (
                    <div key={k} style={{ display:'flex', justifyContent:'space-between', fontSize:11, marginBottom:5 }}>
                      <span style={{ color:'#3a5a78' }}>{k}</span>
                      <span style={{ color:'#6080a0' }}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* System */}
            <div className="sys-col">
              <SystemPanel />
            </div>
          </div>
        )}

        {tab === 'PLUGINY' && (
          <div style={{ padding:16, maxWidth:680 }}>
            <div className="panel" style={{ padding:20 }}>
              <PluginStore />
            </div>
          </div>
        )}

        {tab === 'SYSTÉM' && (
          <div style={{ padding:16, maxWidth:480 }}>
            <SystemPanel />
          </div>
        )}
      </main>
    </div>
  )
}
