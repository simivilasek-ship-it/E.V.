import { useEffect, useState } from 'react'
import { useJarvis } from './store/jarvis'
import AIOrb from './components/AIOrb'
import ChatPanel from './components/ChatPanel'
import SystemPanel from './components/SystemPanel'
import PluginStore from './components/PluginStore'
import AgentGraph from './components/AgentGraph'
import ToastContainer from './components/Toast'
import DashboardPanel from './components/DashboardPanel'
import MemoryGraph from './components/MemoryGraph'
import AgentTimeline from './components/AgentTimeline'
import SkillGenerator from './components/SkillGenerator'
import CommandPalette from './components/CommandPalette'

const Icons = {
  chat:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="nav-icon"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>,
  plugins:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="nav-icon"><path d="M20.24 12.24a6 6 0 00-8.49-8.49L5 10.5V19h8.5z"/><line x1="16" y1="8" x2="2" y2="22"/></svg>,
  system:   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="nav-icon"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>,
  agent:    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="nav-icon"><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>,
  timeline: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="nav-icon"><line x1="12" y1="2" x2="12" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>,
  memory:   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="nav-icon"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>,
  skill:    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="nav-icon"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>,
  dash:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="nav-icon"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>,
}

const TABS = [
  { id: 'CHAT',      label: 'Chat',       icon: Icons.chat },
  { id: 'PLUGINS',   label: 'Plugins',    icon: Icons.plugins },
  { id: 'SYSTEM',    label: 'System',     icon: Icons.system },
  { id: 'AGENT',     label: 'Agent',      icon: Icons.agent },
  { id: 'TIMELINE',  label: 'Timeline',   icon: Icons.timeline },
  { id: 'MEMORY',    label: 'Memory',     icon: Icons.memory },
  { id: 'SKILL',     label: 'Skill Gen',  icon: Icons.skill },
  { id: 'DASHBOARD', label: 'Dashboard',  icon: Icons.dash },
]

const ORB_COLORS = {
  idle:      { label: '○ IDLE',       color: 'var(--text2)' },
  listening: { label: '◉ LISTENING',  color: 'var(--cyan)' },
  thinking:  { label: '◎ THINKING',   color: 'var(--purple)' },
  speaking:  { label: '● SPEAKING',   color: 'var(--green)' },
}

function Sidebar({ tab, setTab, paletteOpen, setPaletteOpen }) {
  const isConn     = useJarvis(s => s.isConnected)
  const connStatus = useJarvis(s => s.connStatus)
  const retry      = useJarvis(s => s.retry)
  const orbState   = useJarvis(s => s.orbState)
  const model      = useJarvis(s => s.currentModel)
  const orb        = ORB_COLORS[orbState] || ORB_COLORS.idle

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="brand-icon"><span>J</span></div>
        <div>
          <div className="brand-name">JARVIS</div>
          <div className="brand-ver">v4.5</div>
        </div>
      </div>

      {/* Connection + orb state */}
      <div className="sidebar-status">
        <div className={`status-dot ${connStatus}`} />
        <button onClick={retry} className="status-label" style={{
          background: 'none', border: 'none', cursor: 'pointer',
          fontFamily: 'var(--font-mono)', fontSize: 9,
          color: { connected: 'var(--green)', connecting: 'var(--amber)',
                   error: 'var(--red)', disconnected: 'var(--text2)', failed: 'var(--red)' }[connStatus] || 'var(--text2)',
          letterSpacing: '.1em',
        }}>
          {connStatus.toUpperCase()}
        </button>
        {model && (
          <div className="status-model" title={model}>{model}</div>
        )}
      </div>

      {/* Orb state */}
      <div style={{ padding: '7px 16px', borderBottom: '1px solid var(--border2)', flexShrink: 0 }}>
        <span style={{
          fontFamily: 'var(--font-hud)',
          fontSize: 8,
          letterSpacing: '.18em',
          color: orb.color,
          textShadow: orbState !== 'idle' ? `0 0 10px ${orb.color}` : 'none',
          transition: 'all .4s',
        }}>
          {orb.label}
        </span>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        {TABS.map(t => (
          <button key={t.id} className={`nav-item ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}>
            {t.icon}
            {t.label}
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <button className="kb-hint" onClick={() => setPaletteOpen(true)}>
          <kbd>⌘K</kbd>
          <span>Command Palette</span>
        </button>
      </div>
    </aside>
  )
}

export default function App() {
  const connect        = useJarvis(s => s.connect)
  const connectMetrics = useJarvis(s => s.connectMetrics)
  const connectChat    = useJarvis(s => s.connectChat)
  const connError      = useJarvis(s => s.connError)
  const retry          = useJarvis(s => s.retry)
  const orbState       = useJarvis(s => s.orbState)
  const [tab, setTab]  = useState('CHAT')
  const [paletteOpen, setPaletteOpen] = useState(false)

  useEffect(() => { connect(); connectMetrics(); connectChat() }, [])

  useEffect(() => {
    const h = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setPaletteOpen(p => !p)
      }
      if (e.key === 'Escape') setPaletteOpen(false)
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

  const orbGlow = {
    idle:      'rgba(0,200,255,.12)',
    listening: 'rgba(0,200,255,.45)',
    thinking:  'rgba(168,85,247,.35)',
    speaking:  'rgba(34,211,165,.35)',
  }[orbState]

  return (
    <div className="app">
      <Sidebar tab={tab} setTab={setTab} paletteOpen={paletteOpen} setPaletteOpen={setPaletteOpen} />

      <div className="main-content">
        {/* Error banner */}
        {connError && (
          <div className="error-banner">
            <span style={{ color: 'var(--red)', fontSize: 13 }}>⚠</span>
            <span style={{ color: 'rgba(244,63,94,.85)', flex: 1 }}>{connError}</span>
            <button onClick={retry} style={{
              padding: '3px 12px', borderRadius: 5, fontSize: 9, cursor: 'pointer',
              background: 'rgba(244,63,94,.1)', color: 'var(--red)',
              border: '1px solid rgba(244,63,94,.25)',
              fontFamily: 'var(--font-hud)', letterSpacing: '.1em',
            }}>RETRY</button>
          </div>
        )}

        {/* Pages */}
        <div className="page">
          {tab === 'CHAT' && (
            <div className="chat-layout">
              {/* Chat */}
              <div className="panel chat-panel"><ChatPanel /></div>

              {/* Orb */}
              <div className="orb-col">
                <div className="panel orb-panel" style={{
                  boxShadow: `var(--card-shadow), 0 0 40px ${orbGlow}`,
                  transition: 'box-shadow 1.2s ease',
                }}>
                  <AIOrb size={240} />
                  <div className="orb-state-label" style={{
                    color: { idle: 'var(--text2)', listening: 'var(--cyan)', thinking: 'var(--purple)', speaking: 'var(--green)' }[orbState],
                    textShadow: orbState !== 'idle' ? '0 0 12px currentColor' : 'none',
                  }}>
                    {{ idle: '○ IDLE', listening: '◉ LISTENING', thinking: '◎ PROCESSING', speaking: '● SPEAKING' }[orbState]}
                  </div>
                </div>

                {/* Shortcuts */}
                <div className="panel shortcuts-panel">
                  <div className="panel-title" style={{ marginBottom: 10 }}>SHORTCUTS</div>
                  {[['↵ Enter', 'Send'], ['⇧ Enter', 'New line'], ['↑ ↓', 'History'], ['⌘K', 'Palette']].map(([k, v]) => (
                    <div key={k} className="shortcut-row">
                      <span className="shortcut-key">{k}</span>
                      <span className="shortcut-desc">{v}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* System */}
              <div className="sys-col"><SystemPanel /></div>
            </div>
          )}

          {tab === 'PLUGINS' && (
            <div className="page-wrap-center">
              <div className="panel" style={{ padding: 20 }}><PluginStore /></div>
            </div>
          )}

          {tab === 'SYSTEM' && (
            <div style={{ padding: 10, maxWidth: 480, height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column', gap: 8 }}>
              <SystemPanel fullMode />
            </div>
          )}

          {tab === 'AGENT' && (
            <div className="page-wrap-center">
              <div className="panel" style={{ padding: 0 }}>
                <AgentGraph active={tab === 'AGENT'} />
              </div>
            </div>
          )}

          {tab === 'TIMELINE' && (
            <div className="page-wrap-center"><AgentTimeline /></div>
          )}

          {tab === 'MEMORY' && (
            <div className="page-wrap-center"><MemoryGraph /></div>
          )}

          {tab === 'SKILL' && (
            <div className="page-wrap-center"><SkillGenerator /></div>
          )}

          {tab === 'DASHBOARD' && (
            <div className="page-wrap" style={{ maxWidth: 1100, margin: '0 auto', width: '100%' }}>
              <DashboardPanel />
            </div>
          )}
        </div>
      </div>

      <ToastContainer />
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onNavigate={setTab}
        onModelChange={(model) => { useJarvis.getState().setModel?.(model) }}
      />
    </div>
  )
}
