import { useEffect, useState, useCallback } from 'react'
import { useJarvis } from './store/jarvis'

function useTheme() {
  const [theme, setTheme] = useState(() => localStorage.getItem('jarvis-theme') || 'dark')
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('jarvis-theme', theme)
  }, [theme])
  const toggle = useCallback(() => setTheme(t => t === 'dark' ? 'light' : 'dark'), [])
  return [theme, toggle]
}
import ChatPanel from './components/ChatPanel'
import SystemPanel from './components/SystemPanel'
import PluginStore from './components/PluginStore'
import AgentGraph from './components/AgentGraph'
import ToastContainer from './components/Toast'
import DashboardPanel from './components/DashboardPanel'
import MemoryGraph from './components/MemoryGraph'
import AgentTimeline from './components/AgentTimeline'
import WorkTimeline from './components/WorkTimeline'
import ActivityFeed from './components/ActivityFeed'
import MissionControl from './components/MissionControl'
import SkillGenerator from './components/SkillGenerator'
import CommandPalette from './components/CommandPalette'

// ── Icons ───────────────────────────────────────────
const I = {
  chat:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>,
  plugins:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M20.24 12.24a6 6 0 00-8.49-8.49L5 10.5V19h8.5z"/><line x1="16" y1="8" x2="2" y2="22"/></svg>,
  system:   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>,
  agent:    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>,
  timeline: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
  work:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
  feed:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>,
  mission:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>,
  memory:   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>,
  skill:    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>,
  dash:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>,
  plus:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>,
  settings: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>,
}

// Nav skupiny
const NAV_GROUPS = [
  {
    label: null, // bez nadpisu
    items: [
      { id: 'CHAT',     label: 'Chat',      icon: I.chat,     key: '1', hint: 'Hlavní chat' },
    ],
  },
  {
    label: 'NÁSTROJE',
    items: [
      { id: 'SYSTEM',   label: 'Systém',    icon: I.system,   key: '2', hint: 'Metriky CPU/RAM' },
      { id: 'PLUGINS',  label: 'Pluginy',   icon: I.plugins,  key: '3', hint: 'Plugin store' },
      { id: 'SKILL',    label: 'Skill Gen', icon: I.skill,    key: '4', hint: 'Generátor skillů' },
    ],
  },
  {
    label: 'INTELIGENCE',
    items: [
      { id: 'WORK',     label: 'Dnes',      icon: I.work,     key: '5', hint: 'Work Timeline' },
      { id: 'FEED',     label: 'Feed',      icon: I.feed,     key: '6', hint: 'Activity Feed' },
      { id: 'MISSIONS', label: 'Missions',  icon: I.mission,  key: '7', hint: 'Mission Control' },
      { id: 'AGENT',    label: 'Agent',     icon: I.agent,    key: '8', hint: 'Graf agentů' },
      { id: 'TIMELINE', label: 'Timeline',  icon: I.timeline, key: '9', hint: 'Agent kroky' },
      { id: 'MEMORY',   label: 'Paměť',     icon: I.memory,   key: '0', hint: 'Knowledge graph' },
    ],
  },
  {
    label: 'MONITOR',
    items: [
      { id: 'DASHBOARD',label: 'Dashboard', icon: I.dash,     key: '-', hint: 'Přehled systému' },
    ],
  },
]

const CONN_COLORS = {
  connected:    '#22d3a5',
  connecting:   '#f59e0b',
  disconnected: '#4d7090',
  error:        '#f43f5e',
  failed:       '#f43f5e',
}

const ORB_CFG = {
  idle:      { label: 'IDLE',       dot: '#4d7090', glow: false },
  listening: { label: 'LISTENING',  dot: '#00c8ff', glow: true },
  thinking:  { label: 'THINKING',   dot: '#a855f7', glow: true },
  speaking:  { label: 'SPEAKING',   dot: '#22d3a5', glow: true },
}

// ── Sidebar ─────────────────────────────────────────
function Sidebar({ tab, setTab, setPaletteOpen, clearMessages, theme, toggleTheme }) {
  const connStatus = useJarvis(s => s.connStatus)
  const retry      = useJarvis(s => s.retry)
  const orbState   = useJarvis(s => s.orbState)
  const model      = useJarvis(s => s.currentModel)
  const system     = useJarvis(s => s.system)
  const [tooltip, setTooltip] = useState(null)

  const connColor = CONN_COLORS[connStatus] || CONN_COLORS.disconnected
  const orb = ORB_CFG[orbState] || ORB_CFG.idle

  return (
    <aside className="sidebar">

      {/* ── Brand ── */}
      <div className="sidebar-brand">
        <div className="brand-icon"><span>J</span></div>
        <div style={{ minWidth: 0 }}>
          <div className="brand-name">JARVIS</div>
          <div className="brand-sub">Lokální AI asistent</div>
        </div>
      </div>

      {/* ── Status kompaktní blok ── */}
      <div className="sidebar-statusblock">
        {/* Connection */}
        <button onClick={retry} className="statusblock-row" title="Klikni pro reconnect">
          <span className="statusblock-dot" style={{
            background: connColor,
            boxShadow: connStatus === 'connected' ? `0 0 6px ${connColor}` : 'none',
            animation: connStatus === 'connecting' ? 'pulse 1s infinite' : 'none',
          }} />
          <span className="statusblock-label" style={{ color: connColor }}>
            {connStatus === 'connected' ? 'Připojeno' :
             connStatus === 'connecting' ? 'Připojuji…' :
             connStatus === 'failed' ? 'Selhalo' : 'Odpojeno'}
          </span>
          {model && <span className="statusblock-model" title={model}>{model}</span>}
        </button>

        {/* Orb state */}
        <div className="statusblock-row" style={{ cursor: 'default' }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
            background: orb.dot,
            boxShadow: orb.glow ? `0 0 8px ${orb.dot}` : 'none',
            transition: 'all .4s',
          }} />
          <span className="statusblock-label" style={{
            color: orb.glow ? orb.dot : 'var(--text2)',
            textShadow: orb.glow ? `0 0 8px ${orb.dot}` : 'none',
            transition: 'all .4s',
          }}>
            {orb.label}
          </span>
          {system.cpu > 0 && (
            <span style={{
              marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: 9,
              color: system.cpu > 80 ? 'var(--red)' : 'var(--text3)',
            }}>
              CPU {system.cpu}%
            </span>
          )}
        </div>
      </div>

      {/* ── New Chat button ── */}
      <div style={{ padding: '10px 12px 4px', flexShrink: 0 }}>
        <button className="new-chat-btn" onClick={() => { setTab('CHAT'); clearMessages() }}>
          <span style={{ width: 14, height: 14, flexShrink: 0 }}>{I.plus}</span>
          Nový chat
        </button>
      </div>

      {/* ── Nav skupiny ── */}
      <nav className="sidebar-nav">
        {NAV_GROUPS.map((group, gi) => (
          <div key={gi} className="nav-group">
            {group.label && (
              <div className="nav-group-label">{group.label}</div>
            )}
            {group.items.map(item => (
              <button
                key={item.id}
                className={`nav-item ${tab === item.id ? 'active' : ''}`}
                onClick={() => setTab(item.id)}
                onMouseEnter={() => setTooltip(item.id)}
                onMouseLeave={() => setTooltip(null)}
                title={item.hint}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
                {/* Aktivní tab: animovaný dot vpravo */}
                {tab === item.id && (
                  <span style={{
                    marginLeft: 'auto', width: 5, height: 5, borderRadius: '50%',
                    background: '#4ecdc4', boxShadow: '0 0 6px #4ecdc4', flexShrink: 0,
                  }} />
                )}
                {/* Klávesová zkratka — zobrazí se při hoveru */}
                {tooltip === item.id && tab !== item.id && (
                  <span style={{
                    marginLeft: 'auto', fontFamily: 'var(--font-mono)',
                    fontSize: 9, color: 'var(--text3)',
                    background: 'rgba(255,255,255,.05)', border: '1px solid rgba(255,255,255,.08)',
                    borderRadius: 3, padding: '1px 5px', flexShrink: 0,
                  }}>{item.key}</span>
                )}
              </button>
            ))}
          </div>
        ))}
      </nav>

      {/* ── Footer ── */}
      <div className="sidebar-footer">
        <button className="kb-hint" onClick={() => setPaletteOpen(true)}>
          <kbd>⌘K</kbd>
          <span>Command palette</span>
        </button>
        <button onClick={toggleTheme} style={{
          display: 'flex', alignItems: 'center', gap: 7,
          width: '100%', padding: '6px 8px', marginTop: 4,
          background: 'none', border: '1px solid transparent',
          borderRadius: 6, cursor: 'pointer', transition: 'all .18s',
          fontFamily: 'var(--font-mono)', fontSize: 10,
          color: 'var(--text2)', letterSpacing: '.04em',
        }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = 'rgba(255,255,255,.02)' }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'transparent'; e.currentTarget.style.background = 'none' }}
        >
          <span style={{ fontSize: 13 }}>{theme === 'dark' ? '☀️' : '🌙'}</span>
          <span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
        </button>
      </div>
    </aside>
  )
}

// ── App ─────────────────────────────────────────────
export default function App() {
  const [theme, toggleTheme] = useTheme()
  const connect        = useJarvis(s => s.connect)
  const connectMetrics = useJarvis(s => s.connectMetrics)
  const connectChat    = useJarvis(s => s.connectChat)
  const connError      = useJarvis(s => s.connError)
  const clearMessages  = useJarvis(s => s.clearMessages)
  const retry          = useJarvis(s => s.retry)
  const orbState       = useJarvis(s => s.orbState)
  const [tab, setTab]  = useState('CHAT')
  const [paletteOpen, setPaletteOpen] = useState(false)

  useEffect(() => { connect(); connectMetrics(); connectChat() }, [])

  // Klávesové zkratky: ⌘K + čísla 1-8
  useEffect(() => {
    const h = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault(); setPaletteOpen(p => !p); return
      }
      if (e.key === 'Escape') { setPaletteOpen(false); return }
      // Alt+1..8 → navigace
      if (e.altKey && !e.ctrlKey) {
        const allItems = NAV_GROUPS.flatMap(g => g.items)
        const found = allItems.find(i => i.key === e.key)
        if (found) { e.preventDefault(); setTab(found.id) }
      }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

  const orbGlow = {
    idle:      'rgba(0,200,255,.1)',
    listening: 'rgba(0,200,255,.4)',
    thinking:  'rgba(168,85,247,.3)',
    speaking:  'rgba(34,211,165,.3)',
  }[orbState]

  return (
    <div className="app">
      <Sidebar
        tab={tab} setTab={setTab}
        setPaletteOpen={setPaletteOpen}
        clearMessages={clearMessages}
        theme={theme} toggleTheme={toggleTheme}
      />

      <div className="main-content">
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

        <div className="page">
          {tab === 'CHAT' && (
            <div className="chat-page">
              <ChatPanel orbGlow={orbGlow} orbState={orbState} />
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
          {tab === 'WORK'     && <div className="page-wrap-center"><WorkTimeline /></div>}
          {tab === 'FEED'     && <div className="page-wrap-center"><ActivityFeed /></div>}
          {tab === 'MISSIONS' && <div className="page-wrap-center"><MissionControl /></div>}
          {tab === 'TIMELINE' && <div className="page-wrap-center"><AgentTimeline /></div>}
          {tab === 'MEMORY'   && <div className="page-wrap-center"><MemoryGraph /></div>}
          {tab === 'SKILL'    && <div className="page-wrap-center"><SkillGenerator /></div>}
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
