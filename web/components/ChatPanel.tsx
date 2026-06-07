'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { useJarvis, type Message, type MessageMode } from '@/store/jarvis'
import { Icons } from './Icons'
import HeroPanel from './HeroPanel'

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

const QUICK_ACTIONS = [
  { label: 'Přehled PC', cmd: 'Přehled PC' },
  { label: 'Obrazovka', cmd: 'Obrazovka' },
  { label: 'Čas', cmd: 'Čas' },
  { label: 'Počasí', cmd: 'Počasí' },
] as const

const MODE_BADGE: Record<MessageMode, { label: string; color: string; bg: string; border: string }> = {
  copilot: { label: 'Copilot', color: 'var(--cyan)', bg: 'rgba(0,200,255,.08)', border: 'rgba(0,200,255,.2)' },
  akce:    { label: 'Akce',    color: 'var(--amber)', bg: 'rgba(245,158,11,.08)', border: 'rgba(245,158,11,.25)' },
  agent:   { label: 'Agent',   color: 'var(--purple)', bg: 'rgba(168,85,247,.08)', border: 'rgba(168,85,247,.25)' },
}

function formatTime(ts: number) {
  const diff = (Date.now() - ts) / 1000
  if (diff < 60) return 'právě teď'
  if (diff < 3600) return `před ${Math.floor(diff / 60)} min`
  return new Date(ts).toLocaleTimeString('cs', { hour: '2-digit', minute: '2-digit' })
}

function renderContent(text: string) {
  if (!text) return null
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="list-disc ml-5 mb-2 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal ml-5 mb-2 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        h1: ({ children }) => <h1 className="text-base font-bold mb-2 mt-3" style={{ color: 'var(--cyan)' }}>{children}</h1>,
        h2: ({ children }) => <h2 className="text-sm font-semibold mb-1.5 mt-3" style={{ color: 'var(--cyan)' }}>{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-semibold mb-1 mt-2" style={{ color: 'rgba(0,200,255,.7)' }}>{children}</h3>,
        strong: ({ children }) => <strong className="font-semibold" style={{ color: '#e2e8f0' }}>{children}</strong>,
        em: ({ children }) => <em className="italic" style={{ color: 'rgba(219,234,254,.7)' }}>{children}</em>,
        code: ({ children, className }) => {
          const isBlock = className?.startsWith('language-')
          if (isBlock) return <code className="prose-j block">{children}</code>
          return <code className="prose-j">{children}</code>
        },
        pre: ({ children }) => <pre className="prose-j mb-2">{children}</pre>,
        a: ({ href, children }) => <a href={href} target="_blank" rel="noreferrer" className="underline" style={{ color: 'var(--cyan)' }}>{children}</a>,
        blockquote: ({ children }) => <blockquote className="border-l-2 pl-3 my-2 italic" style={{ borderColor: 'var(--cyan)', color: 'var(--muted)' }}>{children}</blockquote>,
        hr: () => <hr className="my-3" style={{ borderColor: 'rgba(255,255,255,.08)' }} />,
      }}
    >
      {text}
    </ReactMarkdown>
  )
}

function TypingDots() {
  return (
    <div className="flex gap-1 py-1">
      {[0, 1, 2].map(i => (
        <div key={i} className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }} />
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
          {msg.mode && (
            <span className="px-1.5 py-px rounded-full text-[8px] font-semibold tracking-wide"
              style={{
                color: MODE_BADGE[msg.mode].color,
                background: MODE_BADGE[msg.mode].bg,
                border: `1px solid ${MODE_BADGE[msg.mode].border}`,
              }}>
              {MODE_BADGE[msg.mode].label}
            </span>
          )}
          <span style={{ color: 'var(--muted)' }}>·</span>
          <span style={{ color: 'var(--muted)' }}>{formatTime(msg.ts)}</span>
        </div>
        <div className="group relative text-sm leading-[1.75]" style={{ color: 'rgba(219,234,254,.9)' }}>
          {renderContent(msg.text)}
          {msg.streaming && !msg.text && <TypingDots />}
          {msg.streaming && msg.text && (
            <span className="inline-block w-2 h-3.5 rounded-sm ml-0.5 align-middle anim-blink"
              style={{ background: 'var(--cyan)', boxShadow: '0 0 6px var(--cyan)' }}/>
          )}
          {!msg.streaming && msg.text && (
            <button onClick={copy}
              className="copy-btn absolute top-0 right-0 font-mono text-[10px] px-2 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity"
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
  const isMicActive = useJarvis(s => s.isMicActive)
  const toggleMic = useJarvis(s => s.toggleMic)
  const bottomRef = useRef<HTMLDivElement>(null)
  const taRef     = useRef<HTMLTextAreaElement>(null)
  const [hist, setHist] = useState<string[]>([])
  const [hidx, setHidx] = useState(-1)
  const [plIdx, setPlIdx] = useState(0)
  const [dragOver, setDragOver] = useState(false)
  const [pendingImage, setPendingImage] = useState<string | null>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => {
    const t = setInterval(() => setPlIdx(i => (i + 1) % PLACEHOLDERS.length), 3200)
    return () => clearInterval(t)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (ev) => {
        const base64 = ev.target?.result as string
        setPendingImage(base64)
      }
      reader.readAsDataURL(file)
    }
  }, [])

  const send = useCallback(() => {
    const t = input.trim()
    if (!t && !pendingImage || orbState === 'thinking') return
    const text = pendingImage
      ? `[OBRAZ:${pendingImage.substring(0, 100)}...] ${t}`
      : t
    setHist(h => [text, ...h.slice(0, 49)]); setHidx(-1); setInput('')
    if (taRef.current) taRef.current.style.height = 'auto'
    setPendingImage(null)
    sendCmd(text); taRef.current?.focus()
  }, [input, pendingImage, orbState, sendCmd])

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
    <div
      className="flex flex-col flex-1 overflow-hidden"
      onDragOver={e => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragOver(false) }}
      onDrop={handleDrop}
      style={dragOver ? { outline: '2px solid rgba(0,200,255,.6)', outlineOffset: -2, borderRadius: 12 } : undefined}
    >

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

      {/* Messages or Hero Panel */}
      <div className="flex-1 overflow-y-auto flex flex-col items-center">
        {messages.length === 0 ? (
          <HeroPanel onSend={(cmd) => { sendCmd(cmd) }} />
        ) : (
          <div className="w-full max-w-[760px] flex flex-col justify-end min-h-full px-5 pt-6 pb-2">
            {messages.map(m => <MessageBubble key={m.id} msg={m} />)}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Suggestions — jen při prázdném chatu (pod hero) */}
      {messages.length === 0 && false && (
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
        {/* Quick actions */}
        <div className="flex flex-wrap gap-1.5 justify-center">
          {QUICK_ACTIONS.map(({ label, cmd }) => (
            <button
              key={label}
              type="button"
              onClick={() => sendCmd(cmd)}
              disabled={busy}
              className="font-mono text-[10px] px-3 py-1 rounded-full transition-all"
              style={{
                background: 'rgba(78,205,196,.05)',
                border: '1px solid rgba(78,205,196,.18)',
                color: 'rgba(78,205,196,.85)',
                cursor: busy ? 'not-allowed' : 'pointer',
                opacity: busy ? 0.5 : 1,
              }}
              onMouseEnter={e => {
                if (busy) return
                const el = e.currentTarget as HTMLElement
                el.style.background = 'rgba(78,205,196,.12)'
                el.style.borderColor = 'rgba(78,205,196,.35)'
                el.style.color = 'var(--teal)'
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLElement
                el.style.background = 'rgba(78,205,196,.05)'
                el.style.borderColor = 'rgba(78,205,196,.18)'
                el.style.color = 'rgba(78,205,196,.85)'
              }}>
              {label}
            </button>
          ))}
        </div>

        {/* Pending image thumbnail */}
        {pendingImage && (
          <div className="flex items-center gap-2 px-1">
            <div className="relative inline-block">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={pendingImage} alt="pending" className="h-14 w-14 rounded-lg object-cover"
                style={{ border: '1px solid rgba(0,200,255,.3)' }} />
              <button
                onClick={() => setPendingImage(null)}
                className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold"
                style={{ background: 'rgba(239,68,68,.85)', color: '#fff', border: '1px solid rgba(0,0,0,.3)' }}>
                ✕
              </button>
            </div>
            <span className="font-mono text-[10px]" style={{ color: 'var(--muted)' }}>Obrázek připraven k odeslání</span>
          </div>
        )}

        {/* Drag over overlay hint */}
        {dragOver && (
          <div className="text-center font-mono text-[11px] py-1" style={{ color: 'var(--cyan)' }}>
            📂 Pusť obrázek pro přiložení
          </div>
        )}

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
          <button
            type="button"
            onClick={toggleMic}
            disabled={busy}
            title={isMicActive ? 'Zastavit mikrofon' : 'Mluvit (Web Speech API)'}
            className="w-10 h-10 rounded-[10px] shrink-0 flex items-center justify-center transition-all"
            style={{
              background: isMicActive ? 'rgba(244,63,94,.15)' : 'rgba(255,255,255,.04)',
              border: isMicActive ? '1px solid rgba(244,63,94,.35)' : '1px solid rgba(255,255,255,.08)',
              color: isMicActive ? 'var(--red)' : 'var(--muted)',
              cursor: busy ? 'not-allowed' : 'pointer',
              boxShadow: isMicActive ? '0 0 14px rgba(244,63,94,.25)' : 'none',
            }}>
            {Icons.mic}
          </button>
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
          <button onClick={send} disabled={busy || (!input.trim() && !pendingImage)}
            className="w-10 h-10 rounded-[10px] shrink-0 flex items-center justify-center transition-all"
            style={{
              background: (input.trim() || pendingImage) && !busy ? 'linear-gradient(135deg,#4ecdc4,#3b82f6)' : 'rgba(255,255,255,.04)',
              border: 'none',
              color: (input.trim() || pendingImage) && !busy ? '#000' : 'var(--muted)',
              cursor: (input.trim() || pendingImage) && !busy ? 'pointer' : 'not-allowed',
              boxShadow: (input.trim() || pendingImage) && !busy ? '0 0 18px rgba(78,205,196,.35)' : 'none',
            }}>
            {busy
              ? <div className="w-4 h-4 rounded-full anim-spin" style={{ border: '2px solid var(--muted)', borderTopColor: 'transparent' }}/>
              : Icons.send
            }
          </button>
        </div>

        <div className="text-center font-mono text-[9px]" style={{ color: 'var(--muted)' }}>
          ↵ odeslat · 🎤 hlas (Chrome) · ⇧↵ nový řádek · ↑↓ historie
        </div>
      </div>
    </div>
  )
}
