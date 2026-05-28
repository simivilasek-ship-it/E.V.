import { useEffect, useState } from 'react'
import { useJarvis } from './store/jarvis'
import AIOrb from './components/AIOrb'
import ChatPanel from './components/ChatPanel'
import SystemPanel from './components/SystemPanel'
import PluginStore from './components/PluginStore'
import ParticleBackground from './components/ParticleBackground'

const NAV_ITEMS = ['CHAT', 'PLUGINY', 'SYSTÉM']

export default function App() {
  const connect   = useJarvis(s => s.connect)
  const isConn    = useJarvis(s => s.isConnected)
  const orbState  = useJarvis(s => s.orbState)
  const [tab, setTab] = useState('CHAT')

  useEffect(() => { connect() }, [])

  return (
    <div className="min-h-screen relative" style={{ background: '#070b12' }}>
      <ParticleBackground />

      {/* Main content above particles */}
      <div className="relative flex flex-col min-h-screen" style={{ zIndex: 1 }}>

        {/* Top bar */}
        <header className="glass border-b sticky top-0" style={{ borderColor: 'rgba(0,212,255,0.12)', zIndex: 10 }}>
          <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-6">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 relative">
                <div className="absolute inset-0 rounded-full"
                  style={{ background: 'radial-gradient(circle, rgba(0,212,255,0.3) 0%, transparent 70%)',
                           animation: 'pulse-glow 2s ease-in-out infinite' }} />
                <div className="w-8 h-8 rounded-full border flex items-center justify-center text-xs"
                  style={{ borderColor: 'rgba(0,212,255,0.5)', color: '#00d4ff' }}>J</div>
              </div>
              <span className="text-sm tracking-widest glow-text" style={{ color: '#00d4ff' }}>
                JARVIS
              </span>
              <span className="text-xs px-2 py-0.5 rounded"
                style={{ background: 'rgba(0,212,255,0.08)', color: '#4a6080', border: '1px solid #1a3050' }}>
                v4.3
              </span>
            </div>

            {/* Nav */}
            <nav className="flex gap-1 ml-4">
              {NAV_ITEMS.map(t => (
                <button key={t} onClick={() => setTab(t)}
                  className="px-4 py-1.5 rounded text-xs tracking-wider transition-all"
                  style={{
                    color: tab === t ? '#00d4ff' : '#4a6080',
                    background: tab === t ? 'rgba(0,212,255,0.08)' : 'transparent',
                    border: `1px solid ${tab === t ? 'rgba(0,212,255,0.3)' : 'transparent'}`,
                  }}>
                  {t}
                </button>
              ))}
            </nav>

            {/* Status right */}
            <div className="ml-auto flex items-center gap-4">
              <div className="flex items-center gap-2 text-xs" style={{ color: '#4a6080' }}>
                <div className="w-1.5 h-1.5 rounded-full"
                  style={{ background: isConn ? '#00e676' : '#ff5252',
                           boxShadow: isConn ? '0 0 6px #00e676' : 'none' }} />
                {isConn ? 'online' : 'offline'}
              </div>
              <div className="text-xs" style={{
                color: { idle:'#4a6080', listening:'#00d4ff', thinking:'#7c4dff', speaking:'#00e676' }[orbState]
              }}>
                {{ idle:'○ idle', listening:'◉ listening', thinking:'◎ thinking', speaking:'● speaking' }[orbState]}
              </div>
            </div>
          </div>
        </header>

        {/* Body */}
        <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-6">
          {tab === 'CHAT' && (
            <div className="grid gap-6" style={{ gridTemplateColumns: '1fr 300px 280px', height: 'calc(100vh - 120px)' }}>
              {/* Chat */}
              <div style={{ minHeight: 0 }}>
                <ChatPanel />
              </div>

              {/* Orb column */}
              <div className="flex flex-col items-center gap-4">
                <div className="glass rounded-xl p-4 flex flex-col items-center w-full neon-border">
                  <AIOrb size={260} />
                </div>
                <div className="glass rounded-xl p-4 w-full text-xs" style={{ color: '#4a6080' }}>
                  <div className="mb-2 tracking-widest">ZKRATKY</div>
                  <div className="space-y-1">
                    <div className="flex justify-between"><span>Enter</span><span style={{ color: '#7ea8d4' }}>odeslat</span></div>
                    <div className="flex justify-between"><span>Ctrl+L</span><span style={{ color: '#7ea8d4' }}>clear</span></div>
                  </div>
                </div>
              </div>

              {/* System */}
              <div style={{ minHeight: 0 }}>
                <SystemPanel />
              </div>
            </div>
          )}

          {tab === 'PLUGINY' && (
            <div style={{ maxWidth: 700 }}>
              <PluginStore />
            </div>
          )}

          {tab === 'SYSTÉM' && (
            <div style={{ maxWidth: 500 }}>
              <SystemPanel />
            </div>
          )}
        </main>

        {/* Footer */}
        <footer className="border-t px-6 py-2 text-xs" style={{ borderColor: '#1a3050', color: '#4a6080' }}>
          JARVIS v4.3 · Lokální AI · 100% offline · {new Date().getFullYear()}
        </footer>
      </div>
    </div>
  )
}
