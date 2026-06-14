'use client'
import { useState, useEffect } from 'react'
import { useJarvis } from '@/store/jarvis'
import { Icons } from './Icons'

export type Tab = 'CHAT' | 'SYSTEM' | 'PLUGINS' | 'SKILL' | 'AGENT' | 'WORK' | 'FEED' | 'CHECKLIST' | 'TIMELINE' | 'MEMORY' | 'DASHBOARD' | 'SETTINGS' | 'WORKFLOW' | 'MISSIONS' | 'VISION' | 'VOICE'

interface NavItem { id: Tab; label: string; icon: React.ReactNode; key: string; advanced?: boolean }

const ALL_NAV: NavItem[] = [
  { id: 'CHAT', label: 'Chat', icon: Icons.chat, key: '1' },
  { id: 'VOICE', label: 'Hlas', icon: Icons.mic, key: 'h' },
  { id: 'SYSTEM', label: 'Systém', icon: Icons.system, key: '2' },
  { id: 'TIMELINE', label: 'Timeline', icon: Icons.timeline, key: '6' },
  { id: 'DASHBOARD', label: 'Dashboard', icon: Icons.dash, key: '8' },
  { id: 'SETTINGS', label: 'Nastavení', icon: Icons.settings, key: '9' },
  { id: 'WORKFLOW', label: 'Workflow', icon: Icons.workflow, key: '0', advanced: true },
  { id: 'MISSIONS', label: 'Agent mise', icon: Icons.mission, key: 'm', advanced: true },
  { id: 'AGENT', label: 'Agent', icon: Icons.agent, key: '5', advanced: true },
  { id: 'MEMORY', label: 'Paměť', icon: Icons.memory, key: '7', advanced: true },
  { id: 'VISION', label: 'Vision', icon: Icons.eye, key: 'v', advanced: true },
  { id: 'SKILL', label: 'Skill Gen', icon: Icons.skill, key: '4', advanced: true },
  { id: 'PLUGINS', label: 'Pluginy', icon: Icons.plugins, key: '3', advanced: true },
  { id: 'WORK', label: 'Dnes', icon: Icons.work, key: 'w', advanced: true },
  { id: 'FEED', label: 'Feed', icon: Icons.feed, key: 'f', advanced: true },
  { id: 'CHECKLIST', label: 'Release', icon: Icons.checklist, key: 'c', advanced: true },
]

function useLocalStorage<T>(key: string, defaultValue: T): [T, React.Dispatch<React.SetStateAction<T>>] {
  const [value, setValue] = useState<T>(() => {
    if (typeof window === 'undefined') return defaultValue
    try {
      const stored = window.localStorage.getItem(key)
      return stored !== null ? (JSON.parse(stored) as T) : defaultValue
    } catch {
      return defaultValue
    }
  })

  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(value))
    } catch {
      // ignore storage errors
    }
  }, [key, value])

  return [value, setValue]
}

function NavButton({ item, tab, setTab }: { item: NavItem; tab: Tab; setTab: (t: Tab) => void }) {
  return (
    <button
      onClick={() => setTab(item.id)}
      title={`Alt+${item.key}`}
      data-testid={`nav-item-${item.id.toLowerCase()}`}
      className={`nav-item ${tab === item.id ? 'active' : ''}`}
    >
      <span className="w-4 h-4 shrink-0 flex items-center justify-center opacity-80">
        {item.icon}
      </span>
      <span className="flex-1 truncate">{item.label}</span>
    </button>
  )
}

const CONN_COLOR: Record<string, string> = {
  connected: 'var(--green)', connecting: 'var(--amber)',
  disconnected: 'var(--muted)', error: 'var(--red)', failed: 'var(--red)',
}

const ORB_CFG: Record<string, { label: string; color: string }> = {
  idle:      { label: 'Připraven',   color: 'var(--muted)' },
  listening: { label: 'Poslouchám',  color: 'var(--cyan)' },
  thinking:  { label: 'Přemýšlím',  color: 'var(--purple)' },
  speaking:  { label: 'Mluvím',      color: 'var(--green)' },
}

interface SidebarProps {
  tab: Tab
  setTab: (t: Tab) => void
  setPaletteOpen: (v: boolean) => void
  setSpotlightOpen?: (v: boolean) => void
  clearMessages: () => void
  theme: string
  toggleTheme: () => void
  isOpen?: boolean
  onClose?: () => void
}

export default function Sidebar({ tab, setTab, setPaletteOpen, setSpotlightOpen, clearMessages, theme, toggleTheme, isOpen = false, onClose }: SidebarProps) {
  const [advanced, setAdvanced] = useLocalStorage<boolean>('jarvis_advanced_mode', false)
  const connStatus = useJarvis(s => s.connStatus)
  const retry      = useJarvis(s => s.retry)
  const orbState   = useJarvis(s => s.orbState)
  const model      = useJarvis(s => s.currentModel)
  const system     = useJarvis(s => s.system)

  const connColor = CONN_COLOR[connStatus] ?? 'var(--muted)'
  const orb = ORB_CFG[orbState] ?? ORB_CFG.idle

  const visibleNav = ALL_NAV.filter(item => advanced || !item.advanced)

  const handleSetTab = (t: Tab) => {
    setTab(t)
    onClose?.()
  }

  return (
    <aside
      data-testid="sidebar"
      className={`flex flex-col h-full relative z-20 glass-panel shrink-0 sidebar-mobile-hidden${isOpen ? ' sidebar-mobile-open' : ''}`}
      style={{ width: 'var(--sidebar-w)', borderRight: '1px solid var(--border)', borderRadius: 0 }}
    >
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 py-5 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
        <div
          className="flex items-center justify-center shrink-0 rounded-xl anim-orb-glow"
          style={{
            width: 44, height: 44,
            background: 'linear-gradient(135deg, var(--accent) 0%, #4f46e5 50%, #7c3aed 100%)',
          }}
        >
          <span className="font-display text-lg font-bold text-white">J</span>
        </div>
        <div className="flex-1">
          <div className="font-display text-base font-bold tracking-tight" style={{ color: 'var(--text)' }}>
            JARVIS
          </div>
          <div className="text-[11px] font-mono" style={{ color: 'var(--muted)' }}>
            v5.15 · Work OS
          </div>
        </div>
        <button
          onClick={onClose}
          className="md:hidden btn-ghost w-7 h-7 flex items-center justify-center text-base shrink-0"
          aria-label="Zavřít menu"
          style={{ color: 'var(--muted)' }}
        >
          ×
        </button>
      </div>

      {/* Status */}
      <div className="px-3 py-3 shrink-0 flex flex-col gap-2" style={{ borderBottom: '1px solid var(--border)' }}>
        <button
          onClick={retry}
          className="status-pill w-full justify-between hover:opacity-90 transition-opacity"
          title="Klikni pro reconnect"
        >
          <span className="flex items-center gap-2">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{
                background: connColor,
                boxShadow: connStatus === 'connected' ? `0 0 8px ${connColor}` : 'none',
                animation: connStatus === 'connecting' ? 'pulseDot 1s infinite' : 'none',
              }}
            />
            <span style={{ color: connColor }}>
              {connStatus === 'connected' ? 'Online' : connStatus === 'connecting' ? 'Připojuji…' :
               connStatus === 'failed' ? 'Selhalo' : 'Offline'}
            </span>
          </span>
          {model && (
            <span className="truncate max-w-[90px] text-[10px]" style={{ color: 'var(--muted)' }} title={model}>
              {model.split(':')[0]}
            </span>
          )}
        </button>

        <div className="flex items-center justify-between px-1">
          <span className="status-pill" style={{ color: orb.color, borderColor: 'var(--border)' }}>
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: orb.color }} />
            {orb.label}
          </span>
          {system.cpu > 0 && (
            <span className="font-mono text-[10px]" style={{ color: system.cpu > 80 ? 'var(--red)' : 'var(--muted)' }}>
              CPU {system.cpu}%
            </span>
          )}
        </div>
      </div>

      {/* New chat */}
      <div className="px-3 pt-3 pb-1 shrink-0">
        <button
          onClick={() => { setTab('CHAT'); clearMessages(); onClose?.() }}
          className="btn-primary flex items-center justify-center gap-2 w-full py-2.5 text-sm"
        >
          {Icons.plus}
          Nový chat
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2.5 py-2 flex flex-col gap-0.5">
        {visibleNav.map(item => (
          <NavButton key={item.id} item={item} tab={tab} setTab={handleSetTab} />
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 shrink-0 flex flex-col gap-1" style={{ borderTop: '1px solid var(--border)' }}>
        <button onClick={() => setPaletteOpen(true)} className="btn-ghost flex items-center gap-2 w-full px-3 py-2 text-xs font-mono">
          <kbd className="px-1.5 py-0.5 rounded text-[10px]" style={{ background: 'rgba(255,255,255,.06)', border: '1px solid var(--border)' }}>⌘K</kbd>
          Paleta příkazů
        </button>
        {setSpotlightOpen && (
          <button onClick={() => setSpotlightOpen(true)} className="btn-ghost flex items-center gap-2 w-full px-3 py-2 text-xs">
            <kbd className="px-1.5 py-0.5 rounded text-[10px] font-mono" style={{ background: 'rgba(99,102,241,.1)', border: '1px solid var(--border-accent)', color: 'var(--accent-light)' }}>Alt+Space</kbd>
            Spotlight
          </button>
        )}
        <button
          onClick={() => setAdvanced(a => !a)}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-colors"
          style={{
            color: 'var(--muted)',
            background: advanced ? 'rgba(99,102,241,.08)' : 'transparent',
          }}
        >
          <span>{advanced ? '⚙ Pokročilý režim' : '◎ Jednoduchý režim'}</span>
          <span className="ml-auto text-[10px]">{advanced ? 'zapnut' : 'vypnut'}</span>
        </button>
        <button onClick={toggleTheme} className="btn-ghost flex items-center gap-2 w-full px-3 py-2 text-xs">
          {theme === 'dark' ? Icons.sun : Icons.moon}
          {theme === 'dark' ? 'Světlý režim' : 'Tmavý režim'}
        </button>
      </div>
    </aside>
  )
}
