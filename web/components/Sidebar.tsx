'use client'
import { useState } from 'react'
import { useJarvis } from '@/store/jarvis'
import { Icons } from './Icons'

export type Tab = 'CHAT' | 'SYSTEM' | 'PLUGINS' | 'SKILL' | 'AGENT' | 'TIMELINE' | 'MEMORY' | 'DASHBOARD' | 'SETTINGS'

interface NavItem { id: Tab; label: string; icon: React.ReactNode; key: string; hint: string }
interface NavGroup { label: string | null; items: NavItem[] }

const NAV_GROUPS: NavGroup[] = [
  { label: null, items: [
    { id: 'CHAT',      label: 'Chat',      icon: Icons.chat,     key: '1', hint: 'Hlavní chat' },
  ]},
  { label: 'NÁSTROJE', items: [
    { id: 'SYSTEM',    label: 'Systém',    icon: Icons.system,   key: '2', hint: 'CPU/RAM metriky' },
    { id: 'PLUGINS',   label: 'Pluginy',   icon: Icons.plugins,  key: '3', hint: 'Plugin store' },
    { id: 'SKILL',     label: 'Skill Gen', icon: Icons.skill,    key: '4', hint: 'Generátor skillů' },
  ]},
  { label: 'INTELIGENCE', items: [
    { id: 'AGENT',     label: 'Agent',     icon: Icons.agent,    key: '5', hint: 'Graf agentů' },
    { id: 'TIMELINE',  label: 'Timeline',  icon: Icons.timeline, key: '6', hint: 'Historie akcí' },
    { id: 'MEMORY',    label: 'Paměť',     icon: Icons.memory,   key: '7', hint: 'Knowledge graph' },
  ]},
  { label: 'MONITOR', items: [
    { id: 'DASHBOARD', label: 'Dashboard', icon: Icons.dash,     key: '8', hint: 'Přehled systému' },
    { id: 'SETTINGS',  label: 'Nastavení', icon: Icons.settings, key: '9', hint: 'Konfigurace JARVIS' },
  ]},
]

const CONN_COLOR: Record<string, string> = {
  connected: '#22d3a5', connecting: '#f59e0b',
  disconnected: '#4d7090', error: '#f43f5e', failed: '#f43f5e',
}

const ORB_CFG: Record<string, { label: string; color: string; glow: boolean }> = {
  idle:      { label: 'IDLE',      color: '#4d7090', glow: false },
  listening: { label: 'LISTENING', color: '#00c8ff', glow: true },
  thinking:  { label: 'THINKING',  color: '#a855f7', glow: true },
  speaking:  { label: 'SPEAKING',  color: '#22d3a5', glow: true },
}

interface SidebarProps {
  tab: Tab
  setTab: (t: Tab) => void
  setPaletteOpen: (v: boolean) => void
  setSpotlightOpen?: (v: boolean) => void
  clearMessages: () => void
  theme: string
  toggleTheme: () => void
}

export default function Sidebar({ tab, setTab, setPaletteOpen, setSpotlightOpen, clearMessages, theme, toggleTheme }: SidebarProps) {
  const connStatus = useJarvis(s => s.connStatus)
  const retry      = useJarvis(s => s.retry)
  const orbState   = useJarvis(s => s.orbState)
  const model      = useJarvis(s => s.currentModel)
  const system     = useJarvis(s => s.system)
  const [tooltip, setTooltip] = useState<Tab | null>(null)

  const connColor = CONN_COLOR[connStatus] ?? '#4d7090'
  const orb = ORB_CFG[orbState] ?? ORB_CFG.idle

  return (
    <aside className="flex flex-col h-full relative z-20"
      style={{ width: 220, background: 'rgba(4,9,16,.92)', borderRight: '1px solid var(--border2)' }}>

      {/* Brand */}
      <div className="flex items-center gap-3 px-4 py-[18px] shrink-0"
        style={{ borderBottom: '1px solid var(--border2)' }}>
        <div className="flex items-center justify-center shrink-0 rounded-[13px] anim-logo-pulse"
          style={{
            width: 44, height: 44,
            background: 'linear-gradient(135deg,rgba(78,205,196,.18),rgba(0,200,255,.12),rgba(99,102,241,.1))',
            border: '1px solid rgba(78,205,196,.4)',
          }}>
          <span className="font-hud font-black text-xl leading-none"
            style={{ color: '#4ecdc4', textShadow: '0 0 12px rgba(78,205,196,.8)' }}>J</span>
        </div>
        <div>
          <div className="font-hud font-bold tracking-widest text-sm leading-tight"
            style={{ color: 'var(--cyan)', letterSpacing: '.28em' }}>JARVIS</div>
          <div className="text-[10px] mt-0.5" style={{ color: 'var(--muted)' }}>Lokální AI asistent</div>
        </div>
      </div>

      {/* Status block */}
      <div className="px-3 py-1.5 shrink-0 flex flex-col gap-1"
        style={{ borderBottom: '1px solid var(--border2)' }}>

        <button onClick={retry}
          className="flex items-center gap-2 px-2 py-1 rounded-md w-full hover:bg-white/[.03] transition-colors"
          title="Klikni pro reconnect">
          <span className="w-2 h-2 rounded-full shrink-0 transition-all"
            style={{
              background: connColor,
              boxShadow: connStatus === 'connected' ? `0 0 6px ${connColor}` : 'none',
              animation: connStatus === 'connecting' ? 'pulseDot 1s infinite' : 'none',
            }}/>
          <span className="font-mono text-[10px] tracking-wider transition-all" style={{ color: connColor }}>
            {connStatus === 'connected' ? 'Připojeno' : connStatus === 'connecting' ? 'Připojuji…' :
             connStatus === 'failed' ? 'Selhalo' : 'Odpojeno'}
          </span>
          {model && (
            <span className="ml-auto font-mono text-[9px] px-1.5 py-px rounded truncate max-w-[80px]"
              style={{ color: 'var(--muted)', border: '1px solid var(--border2)' }} title={model}>
              {model}
            </span>
          )}
        </button>

        <div className="flex items-center gap-2 px-2 py-1">
          <span className="w-2 h-2 rounded-full shrink-0 transition-all"
            style={{
              background: orb.color,
              boxShadow: orb.glow ? `0 0 8px ${orb.color}` : 'none',
            }}/>
          <span className="font-mono text-[9px] tracking-widest transition-all"
            style={{ color: orb.color, textShadow: orb.glow ? `0 0 8px ${orb.color}` : 'none' }}>
            {orb.label}
          </span>
          {system.cpu > 0 && (
            <span className="ml-auto font-mono text-[9px]"
              style={{ color: system.cpu > 80 ? 'var(--red)' : 'var(--muted)' }}>
              CPU {system.cpu}%
            </span>
          )}
        </div>
      </div>

      {/* New chat */}
      <div className="px-3 pt-2.5 pb-1 shrink-0">
        <button
          onClick={() => { setTab('CHAT'); clearMessages() }}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-[9px] text-xs font-medium transition-all"
          style={{
            background: 'rgba(78,205,196,.07)', border: '1px solid rgba(78,205,196,.2)',
            color: '#4ecdc4',
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(78,205,196,.13)'; (e.currentTarget as HTMLElement).style.borderColor = 'rgba(78,205,196,.35)' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(78,205,196,.07)'; (e.currentTarget as HTMLElement).style.borderColor = 'rgba(78,205,196,.2)' }}>
          {Icons.plus}
          Nový chat
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2.5 py-1 flex flex-col gap-0.5">
        {NAV_GROUPS.map((group, gi) => (
          <div key={gi} className="mb-1">
            {group.label && (
              <div className="font-hud text-[8px] tracking-[.18em] px-3 pt-2 pb-1"
                style={{ color: 'var(--muted)', opacity: .7 }}>
                {group.label}
              </div>
            )}
            {group.items.map(item => (
              <button
                key={item.id}
                onClick={() => setTab(item.id)}
                onMouseEnter={() => setTooltip(item.id)}
                onMouseLeave={() => setTooltip(null)}
                title={item.hint}
                className={`flex items-center gap-2.5 w-full px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all text-left relative ${
                  tab === item.id ? 'active-nav' : ''
                }`}
                style={{
                  color: tab === item.id ? 'var(--cyan)' : 'var(--muted)',
                  background: tab === item.id ? 'rgba(0,200,255,.07)' : 'transparent',
                  border: tab === item.id ? '1px solid rgba(0,200,255,.12)' : '1px solid transparent',
                }}>
                {/* Active left bar */}
                {tab === item.id && (
                  <span className="absolute left-0 top-[20%] bottom-[20%] w-0.5 rounded-r"
                    style={{ background: '#4ecdc4', boxShadow: '0 0 6px #4ecdc4' }}/>
                )}
                <span className="w-4 h-4 shrink-0 opacity-60 flex items-center justify-center"
                  style={{ opacity: tab === item.id ? 1 : undefined }}>
                  {item.icon}
                </span>
                <span className="flex-1 truncate">{item.label}</span>
                {/* Active dot */}
                {tab === item.id && (
                  <span className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ background: '#4ecdc4', boxShadow: '0 0 6px #4ecdc4' }}/>
                )}
                {/* Kbd hint on hover */}
                {tooltip === item.id && tab !== item.id && (
                  <span className="ml-auto font-mono text-[9px] px-1 py-px rounded shrink-0"
                    style={{ color: 'var(--muted)', background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.07)' }}>
                    {item.key}
                  </span>
                )}
              </button>
            ))}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 shrink-0 flex flex-col gap-1"
        style={{ borderTop: '1px solid var(--border2)' }}>
        <button onClick={() => setPaletteOpen(true)}
          className="flex items-center gap-2 w-full px-2 py-1.5 rounded-md font-mono text-[9px] tracking-wide transition-all"
          style={{ color: 'var(--muted)', border: '1px solid transparent' }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--border2)'; (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,.02)' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'transparent'; (e.currentTarget as HTMLElement).style.background = 'none' }}>
          <kbd className="px-1 py-px rounded text-[9px]"
            style={{ background: 'rgba(255,255,255,.06)', border: '1px solid rgba(255,255,255,.1)', color: 'var(--muted)' }}>
            ⌘K
          </kbd>
          <span>Command palette</span>
        </button>
        {setSpotlightOpen && (
          <button onClick={() => setSpotlightOpen(true)}
            className="flex items-center gap-2 w-full px-2 py-1.5 rounded-md font-mono text-[10px] transition-all"
            style={{ color: '#4ecdc4', border: '1px solid transparent' }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(78,205,196,.25)'; (e.currentTarget as HTMLElement).style.background = 'rgba(78,205,196,.05)' }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'transparent'; (e.currentTarget as HTMLElement).style.background = 'none' }}>
            <kbd className="px-1 py-px rounded text-[9px]"
              style={{ background: 'rgba(78,205,196,.1)', border: '1px solid rgba(78,205,196,.3)', color: '#4ecdc4' }}>
              Alt+Space
            </kbd>
            <span>Spotlight</span>
          </button>
        )}
        <button onClick={toggleTheme}
          className="flex items-center gap-2 w-full px-2 py-1.5 rounded-md font-mono text-[10px] transition-all"
          style={{ color: 'var(--muted)', border: '1px solid transparent' }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'var(--border2)'; (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,.02)' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'transparent'; (e.currentTarget as HTMLElement).style.background = 'none' }}>
          {theme === 'dark' ? Icons.sun : Icons.moon}
          {theme === 'dark' ? 'Light mode' : 'Dark mode'}
        </button>
      </div>
    </aside>
  )
}
