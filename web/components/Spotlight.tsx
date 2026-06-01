'use client'
import { useEffect, useRef, useState, lazy, Suspense } from 'react'
import { useJarvis } from '@/store/jarvis'

const WeatherWidget = lazy(() => import('./widgets/WeatherWidget'))
const SystemWidget  = lazy(() => import('./widgets/SystemWidget'))
const SportsWidget  = lazy(() => import('./widgets/SportsWidget'))
const ClockWidget   = lazy(() => import('./widgets/ClockWidget'))
const CalcWidget    = lazy(() => import('./widgets/CalcWidget'))

// ── Intent detection ────────────────────────────────
type WidgetType = 'weather' | 'system' | 'sports' | 'clock' | 'calc' | 'command' | null

function detectIntent(q: string): WidgetType {
  const t = q.toLowerCase().trim()
  if (!t) return null
  if (/^(počasí|pocasi|weather|teplota|bude prset)/.test(t)) return 'weather'
  if (/^(systém|system|cpu|ram|disk|hardware|metriky|jak\s+to\s+jede|kolik\s+(cpu|ram))/.test(t)) return 'system'
  if (/^(fotbal|sport|nhl|nba|premier|champions|liga|zapas|vysledky|skore)/.test(t)) return 'sports'
  if (/^(kolik\s+je\s+hodin|cas|hodiny|čas|time|kolik\s+hodin)/.test(t)) return 'clock'
  if (/^(vypočítej|spočítej|kolik\s+je\s+\d|calculate|calc|\d[\d\s+\-*/%.()]+)/.test(t)) return 'calc'
  if (t.length > 2) return 'command'
  return null
}

// Quick suggestions shown when spotlight is empty
const SUGGESTIONS = [
  { icon: '🌤️', label: 'Počasí Praha',    query: 'počasí Praha' },
  { icon: '💻', label: 'Systém',           query: 'system' },
  { icon: '⚽', label: 'Fotbal výsledky', query: 'fotbal' },
  { icon: '🕐', label: 'Kolik je hodin',  query: 'kolik je hodin' },
  { icon: '🧮', label: '15% z 2400',      query: 'vypočítej 15% z 2400' },
]

interface SpotlightProps {
  open: boolean
  onClose: () => void
  onCommand: (cmd: string) => void
}

export default function Spotlight({ open, onClose, onCommand }: SpotlightProps) {
  const [input, setInput]     = useState('')
  const [intent, setIntent]   = useState<WidgetType>(null)
  const [widgetQuery, setWidgetQuery] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const sendCommand = useJarvis(s => s.sendCommand)

  // Focus on open
  useEffect(() => {
    if (open) {
      setInput(''); setIntent(null)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  // Detect intent with debounce
  useEffect(() => {
    const id = setTimeout(() => {
      const i = detectIntent(input)
      setIntent(i)
      if (i && i !== 'command') setWidgetQuery(input)
    }, 250)
    return () => clearTimeout(id)
  }, [input])

  const submit = () => {
    if (!input.trim()) return
    onClose()
    sendCommand(input.trim())
    onCommand(input.trim())
    setInput('')
  }

  if (!open) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[200]"
        style={{ background: 'rgba(2,6,14,.6)', backdropFilter: 'blur(6px)' }}
        onClick={onClose}
      />

      {/* Spotlight panel */}
      <div
        className="fixed z-[201] anim-slide-up"
        style={{
          top: '18vh',
          left: '50%',
          transform: 'translateX(-50%)',
          width: 'min(580px, 94vw)',
        }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{
          background: 'rgba(6,12,26,.97)',
          border: '1px solid rgba(0,200,255,.2)',
          borderRadius: 16,
          boxShadow: '0 24px 64px rgba(0,0,0,.7), 0 0 0 1px rgba(255,255,255,.04) inset',
          overflow: 'hidden',
        }}>

          {/* Input row */}
          <div className="flex items-center gap-3 px-4 py-3" style={{ borderBottom: intent ? '1px solid rgba(0,200,255,.08)' : 'none' }}>
            <span className="text-lg shrink-0" style={{ filter: 'drop-shadow(0 0 6px var(--cyan))' }}>
              {intent === 'weather' ? '🌤️' : intent === 'system' ? '💻' : intent === 'sports' ? '⚽' :
               intent === 'clock' ? '🕐' : intent === 'calc' ? '🧮' : '✦'}
            </span>
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter') submit()
                if (e.key === 'Escape') onClose()
              }}
              placeholder="Příkaz, počasí, sport, výpočet…"
              className="flex-1 bg-transparent border-none outline-none text-base"
              style={{ color: 'var(--text)', fontFamily: "'Inter', system-ui" }}
            />
            {input && (
              <button onClick={() => { setInput(''); setIntent(null) }}
                className="text-xs px-1.5 py-0.5 rounded transition-all"
                style={{ color: 'var(--muted)', background: 'rgba(255,255,255,.05)' }}>
                esc
              </button>
            )}
          </div>

          {/* Widget area */}
          <div className="px-4" style={{ minHeight: intent ? 60 : 0 }}>
            <Suspense fallback={
              <div className="py-3 flex items-center gap-2 text-xs" style={{ color: 'var(--muted)' }}>
                <div className="w-3 h-3 rounded-full border-2 anim-spin" style={{ borderColor: 'var(--cyan)', borderTopColor: 'transparent' }}/>
                Načítám…
              </div>
            }>
              {intent === 'weather' && <WeatherWidget query={widgetQuery} />}
              {intent === 'system'  && <SystemWidget />}
              {intent === 'sports'  && <SportsWidget query={widgetQuery} />}
              {intent === 'clock'   && <ClockWidget query={widgetQuery} />}
              {intent === 'calc'    && <CalcWidget query={widgetQuery} />}
              {intent === 'command' && input.trim() && (
                <div className="py-3 flex items-center justify-between">
                  <span className="text-sm" style={{ color: 'var(--text)' }}>
                    Odeslat: <span style={{ color: 'var(--cyan)' }}>{input}</span>
                  </span>
                  <span className="font-mono text-xs px-2 py-0.5 rounded" style={{ background: 'rgba(0,200,255,.08)', color: 'var(--cyan)', border: '1px solid rgba(0,200,255,.2)' }}>
                    ↵ Enter
                  </span>
                </div>
              )}
            </Suspense>
          </div>

          {/* Suggestions — shown when input is empty */}
          {!input && (
            <div className="px-4 pb-3 pt-1 flex gap-2 flex-wrap">
              {SUGGESTIONS.map(s => (
                <button key={s.query} onClick={() => setInput(s.query)}
                  className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg transition-all"
                  style={{
                    background: 'rgba(255,255,255,.03)',
                    border: '1px solid rgba(255,255,255,.07)',
                    color: 'var(--muted)',
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(0,200,255,.2)'; (e.currentTarget as HTMLElement).style.color = 'var(--text)' }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = 'rgba(255,255,255,.07)'; (e.currentTarget as HTMLElement).style.color = 'var(--muted)' }}>
                  <span>{s.icon}</span>
                  <span>{s.label}</span>
                </button>
              ))}
            </div>
          )}

          {/* Footer hint */}
          <div className="px-4 py-2 font-mono text-[9px] flex gap-4 justify-end"
            style={{ color: 'var(--text3)', borderTop: '1px solid rgba(255,255,255,.04)' }}>
            <span>↵ odeslat</span>
            <span>Esc zavřít</span>
            <span>Alt+Space přepnout</span>
          </div>
        </div>
      </div>
    </>
  )
}
