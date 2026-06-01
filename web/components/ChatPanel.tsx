'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import { useJarvis, type Message } from '@/store/jarvis'
import { Icons } from './Icons'

const PLACEHOLDERS = [
  { text: 'Otevři Spotify…',           tag: 'ovládání PC' },
  { text: 'Počasí Praha…',             tag: 'Open-Meteo' },
  { text: 'Popiš obrazovku…',          tag: 'vision AI' },
  { text: 'Zahraj Bohemian Rhapsody…', tag: 'YouTube' },
  { text: 'Jaké máš komponenty?',      tag: 'hardware' },
  { text: 'Fotbal výsledky dnes…',     tag: 'sport' },
  { text: 'Přelož hello world…',       tag: 'AI překlad' },
  { text: 'Vypočítej 15% z 2400…',     tag: 'kalkulačka' },
]

const SUGGESTIONS = ['kolik je hodin?', 'počasí Praha', 'info o systému', 'screenshot', 'hardware info', 'fotbal výsledky']

function formatTime(ts: number) {
  const diff = (Date.now() - ts) / 1000
  if (diff < 60) return 'právě teď'
  if (diff < 3600) return `před ${Math.floor(diff / 60)} min`
  return new Date(ts).toLocaleTimeString('cs', { hour: '2-digit', minute: '2-digit' })
}

function renderContent(text: string) {
  if (!text) return null
  const parts = text.split(/(```[\s\S]*?```)/g)
  return parts.map((p, i) => {
    if (p.startsWith('```')) {
      const lang = p.match(/^```(\w+)/)?.[1] ?? ''
      const code = p.replace(/^```\w*\n?/, '').replace(/\n?```$/, '')
      return (
        <pre key={i} className="prose-j">
          {lang && <span className="float-right font-mono text-[8px]" style={{ color: 'var(--muted)' }}>{lang}</span>}
          {code}
        </pre>
      )
    }
    return (
      <span key={i}>
        {p.split(/(`[^`]+`)/g).map((c, j) =>
          c.startsWith('`') ? <code key={j} className="prose-j">{c.slice(1, -1)}</code> : c
        )}
      </span>
    )
  })
}

function TypingDots() {
  return (
    <div className="flex gap-1 py-0.5">
      {[0, 1, 2].map(i => (
        <span key={i} className="w-1.5 h-1.5 rounded-full anim-bounce"
          style={{ background: 'var(--cyan)', animationDelay: `${i * 0.16}s` }} />
      ))}
    </div>
  )
}

function MessageBubble({ msg }: { msg: Message }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(msg.text ?? '')
    setCopied(true); setTimeout(() => setCopied(false), 1400)
  }

  if (msg.sender === 'user') return (
    <div className="flex justify-end gap-2.5 mb-5 items-end anim-msg-in">
      <div className="max-w-[580px]">
        <div className="px-4 py-2.5 rounded-2xl rounded-br-[3px] text-sm leading-7"
          style={{
            background: 'linear-gradient(135deg,rgba(59,130,246,.18),rgba(99,102,241,.14))',
            border: '1px solid rgba(99,102,241,.25)',
            color: 'var(--text)',
          }}>
          {renderContent(msg.text)}
        </div>
        <div className="text-right mt-1 font-mono text-[9px]" style={{ color: 'var(--muted)' }}>
          {formatTime(msg.ts)}
        </div>
      </div>
      <div className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center font-hud text-[10px] font-bold"
        style={{ background: 'linear-gradient(135deg,rgba(59,130,246,.1),rgba(99,102,241,.08))', border: '1px solid rgba(99,102,241,.25)', color: '#93c5fd' }}>
        U
      </div>
    </div>
  )

  return (
    <div className="flex gap-3 mb-6 items-start anim-msg-in">
      <div className="w-8 h-8 rounded-lg shrink-0 mt-0.5 flex items-center justify-center font-hud text-[10px] font-bold"
        style={{
          background: 'linear-gradient(135deg,rgba(0,200,255,.12),rgba(99,102,241,.08))',
          border: '1px solid rgba(0,200,255,.2)',
          color: 'var(--cyan)', boxShadow: '0 0 12px rgba(0,200,255,.08)',
        }}>J</div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1.5 font-mono text-[10px]">
          <span className="font-semibold tracking-wide" style={{ color: 'rgba(0,200,255,.7)' }}>JARVIS</span>
          <span style={{ color: 'var(--muted)' }}>·</span>
          <span style={{ color: 'var(--muted)' }}>{formatTime(msg.ts)}</span>
        </div>
        <div className="relative text-sm leading-[1.75]" style={{ color: 'rgba(219,234,254,.9)' }}>
          {renderContent(msg.text)}
          {msg.streaming && !msg.text && <TypingDots />}
          {msg.streaming && msg.text && (
            <span className="inline-block w-2 h-3.5 rounded-sm ml-0.5 align-middle anim-blink"
              style={{ background: 'var(--cyan)', boxShadow: '0 0 6px var(--cyan)' }}/>
          )}
          {!msg.streaming && msg.text && (
            <button onClick={copy}
              className="absolute top-0 right-0 font-mono text-[10px] px-2 py-0.5 rounded opacity-0 hover:opacity-100 transition-opacity"
              style={{
                background: copied ? 'rgba(34,211,165,.1)' : 'rgba(0,0,0,.45)',
                border: `1px solid ${copied ? 'rgba(34,211,165,.3)' : 'rgba(255,255,255,.08)'}`,
                color: copied ? 'var(--green)' : 'var(--muted)',
              }}>
              {copied ? '✓' : '⎘'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function ChatPanel() {
  const [input, setInput]     = useState('')
  const messages  = useJarvis(s => s.messages)
  const sendCmd   = useJarvis(s => s.sendCommand)
  const clearMsgs = useJarvis(s => s.clearMessages)
  const orbState  = useJarvis(s => s.orbState)
  const bottomRef = useRef<HTMLDivElement>(null)
  const taRef     = useRef<HTMLTextAreaElement>(null)
  const [hist, setHist] = useState<string[]>([])
  const [hidx, setHidx] = useState(-1)
  const [plIdx, setPlIdx] = useState(0)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => {
    const t = setInterval(() => setPlIdx(i => (i + 1) % PLACEHOLDERS.length), 3200)
    return () => clearInterval(t)
  }, [])

  const send = useCallback(() => {
    const t = input.trim()
    if (!t || orbState === 'thinking') return
    setHist(h => [t, ...h.slice(0, 49)]); setHidx(-1); setInput('')
    if (taRef.current) taRef.current.style.height = 'auto'
    sendCmd(t); taRef.current?.focus()
  }, [input, orbState, sendCmd])

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); return }
    if (e.key === 'ArrowUp' && !input) {
      e.preventDefault(); const n = Math.min(hidx + 1, hist.length - 1); setHidx(n); setInput(hist[n] ?? '')
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault(); const n = Math.max(hidx - 1, -1); setHidx(n); setInput(n === -1 ? '' : hist[n])
    }
  }

  const busy = orbState === 'thinking' || orbState === 'speaking'
  const pl = PLACEHOLDERS[plIdx]

  return (
    <div className="flex flex-col flex-1 overflow-hidden">

      {/* Toolbar */}
      <div className="flex items-center justify-between shrink-0 px-4 py-2.5"
        style={{ borderBottom: '1px solid var(--border2)' }}>
        <span className="font-hud text-[8px] tracking-[.2em]" style={{ color: 'var(--muted)' }}>KOMUNIKACE</span>
        <button onClick={clearMsgs}
          className="font-mono text-[9px] tracking-wider px-2 py-1 rounded transition-colors"
          style={{ color: 'var(--muted)', background: 'none', border: 'none' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--red)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--muted)')}>
          CLEAR
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto flex flex-col items-center">
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 p-8 pointer-events-none">
            {/* Pulsing orb */}
            <div className="relative w-36 h-36 flex items-center justify-center">
              <div className="absolute w-36 h-36 rounded-full anim-orb-outer"
                style={{ border: '1px solid rgba(78,205,196,.35)' }}/>
              <div className="absolute w-28 h-28 rounded-full anim-orb-ring"
                style={{ border: '1.5px solid rgba(78,205,196,.5)', background: 'radial-gradient(circle,rgba(78,205,196,.04) 0%,transparent 70%)' }}/>
              <div className="w-20 h-20 rounded-full flex items-center justify-center anim-orb-inner relative z-10"
                style={{
                  background: 'radial-gradient(circle at 35% 35%,rgba(78,205,196,.22),rgba(0,200,255,.08) 60%,rgba(99,102,241,.06))',
                  border: '1.5px solid rgba(78,205,196,.45)',
                }}>
                <span className="font-hud font-black text-3xl leading-none anim-orb-logo"
                  style={{ color: '#4ecdc4', textShadow: '0 0 16px rgba(78,205,196,.9),0 0 32px rgba(78,205,196,.4)' }}>J</span>
              </div>
            </div>

            <div className="text-center">
              <div className="font-hud font-bold tracking-[.3em] text-base"
                style={{ background: 'linear-gradient(135deg,#4ecdc4,#00c8ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                JARVIS
              </div>
              <div className="text-sm mt-1" style={{ color: 'var(--muted)' }}>Jak ti mohu pomoct?</div>
            </div>
          </div>
        ) : (
          <div className="w-full max-w-[760px] flex flex-col justify-end min-h-full px-5 pt-6 pb-2">
            {messages.map(m => <MessageBubble key={m.id} msg={m} />)}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Suggestions */}
      {messages.length === 0 && (
        <div className="flex flex-wrap gap-1.5 px-4 pb-2 justify-center">
          {SUGGESTIONS.map(s => (
            <button key={s} onClick={() => sendCmd(s)}
              className="font-mono text-[10px] px-3 py-1 rounded-full transition-all"
              style={{
                background: 'rgba(0,200,255,.05)', border: '1px solid rgba(0,200,255,.15)',
                color: 'rgba(0,200,255,.7)',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(0,200,255,.1)'; (e.currentTarget as HTMLElement).style.color = 'var(--cyan)' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(0,200,255,.05)'; (e.currentTarget as HTMLElement).style.color = 'rgba(0,200,255,.7)' }}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="shrink-0 px-4 pb-4 flex flex-col gap-1.5 max-w-[760px] w-full mx-auto">
        {/* Feature tag */}
        {!input && (
          <div className="flex items-center gap-2 pl-0.5">
            <span className="font-mono text-[9px]" style={{ color: 'var(--muted)' }}>JARVIS umí:</span>
            <span className="font-mono text-[9px] px-2 py-0.5 rounded-full"
              style={{ background: 'rgba(78,205,196,.08)', border: '1px solid rgba(78,205,196,.2)', color: '#4ecdc4' }}>
              {pl.tag}
            </span>
          </div>
        )}

        {/* Textarea box */}
        <div className="flex gap-2 items-end rounded-[14px] px-4 py-2 transition-all"
          style={{ background: 'rgba(6,12,26,.85)', border: '1px solid rgba(0,200,255,.16)', boxShadow: '0 4px 24px rgba(0,0,0,.35)' }}>
          <textarea
            ref={taRef}
            value={input}
            onChange={e => {
              setInput(e.target.value)
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
            }}
            onKeyDown={onKey}
            placeholder={pl.text}
            rows={1}
            disabled={busy}
            className="flex-1 bg-transparent border-none resize-none outline-none text-sm leading-[1.55] py-1.5"
            style={{ color: 'var(--text)', fontFamily: "'Inter',system-ui", minHeight: 36, maxHeight: 160 }}
          />
          <button onClick={send} disabled={busy || !input.trim()}
            className="w-10 h-10 rounded-[10px] shrink-0 flex items-center justify-center transition-all"
            style={{
              background: input.trim() && !busy ? 'linear-gradient(135deg,#4ecdc4,#3b82f6)' : 'rgba(255,255,255,.04)',
              border: 'none',
              color: input.trim() && !busy ? '#000' : 'var(--muted)',
              cursor: input.trim() && !busy ? 'pointer' : 'not-allowed',
              boxShadow: input.trim() && !busy ? '0 0 18px rgba(78,205,196,.35)' : 'none',
            }}>
            {busy
              ? <div className="w-4 h-4 rounded-full anim-spin" style={{ border: '2px solid var(--muted)', borderTopColor: 'transparent' }}/>
              : Icons.send
            }
          </button>
        </div>

        <div className="text-center font-mono text-[9px]" style={{ color: 'var(--muted)' }}>
          ↵ odeslat · ⇧↵ nový řádek · ↑↓ historie
        </div>
      </div>
    </div>
  )
}
