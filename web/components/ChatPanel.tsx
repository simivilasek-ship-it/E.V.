'use client'
import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import { useJarvis, type Message, type MessageMode } from '@/store/jarvis'
import { Icons } from './Icons'
import HeroPanel from './HeroPanel'

const PLACEHOLDERS = [
  { text: 'Otevři Spotify…', tag: 'ovládání PC' },
  { text: 'Počasí Praha…', tag: 'počasí' },
  { text: 'Popiš obrazovku…', tag: 'vision' },
  { text: 'Stáhni Instagram…', tag: 'instalace' },
  { text: 'Přehled o PC…', tag: 'systém' },
  { text: 'Fotbal výsledky…', tag: 'sport' },
]

const QUICK_ACTIONS = [
  { label: 'Přehled PC', cmd: 'Přehled PC' },
  { label: 'Obrazovka', cmd: 'Obrazovka' },
  { label: 'Čas', cmd: 'Čas' },
  { label: 'Počasí', cmd: 'Počasí' },
] as const

const MODE_BADGE: Record<MessageMode, { label: string; color: string; bg: string }> = {
  copilot: { label: 'Copilot', color: 'var(--accent-light)', bg: 'rgba(99,102,241,.12)' },
  akce:    { label: 'Akce',    color: 'var(--amber)', bg: 'rgba(251,191,36,.12)' },
  agent:   { label: 'Agent',   color: 'var(--purple)', bg: 'rgba(167,139,250,.12)' },
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
        h1: ({ children }) => <h1 className="text-base font-semibold mb-2 mt-3" style={{ color: 'var(--accent-light)' }}>{children}</h1>,
        h2: ({ children }) => <h2 className="text-sm font-semibold mb-1.5 mt-3" style={{ color: 'var(--accent-light)' }}>{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-medium mb-1 mt-2" style={{ color: 'var(--text-secondary)' }}>{children}</h3>,
        strong: ({ children }) => <strong className="font-semibold" style={{ color: 'var(--text)' }}>{children}</strong>,
        code: ({ children, className }) => {
          const isBlock = className?.startsWith('language-')
          if (isBlock) return <code className="prose-j block">{children}</code>
          return <code className="prose-j">{children}</code>
        },
        pre: ({ children }) => <pre className="prose-j mb-2">{children}</pre>,
        a: ({ href, children }) => <a href={href} target="_blank" rel="noreferrer" className="underline" style={{ color: 'var(--accent-light)' }}>{children}</a>,
        blockquote: ({ children }) => <blockquote className="border-l-2 pl-3 my-2 italic" style={{ borderColor: 'var(--accent)', color: 'var(--muted)' }}>{children}</blockquote>,
      }}
    >
      {text}
    </ReactMarkdown>
  )
}

function TypingDots() {
  return (
    <div className="flex gap-1.5 py-1">
      {[0, 1, 2].map(i => (
        <div key={i} className="w-1.5 h-1.5 rounded-full anim-pulse"
          style={{ background: 'var(--accent-light)', animationDelay: `${i * 0.15}s` }} />
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
    <div className="flex justify-end mb-5 anim-msg-in">
      <div className="max-w-[min(580px,85%)]">
        <div className="msg-user px-4 py-3 text-sm leading-relaxed" style={{ color: 'var(--text)' }}>
          {renderContent(msg.text)}
        </div>
        <div className="text-right mt-1 font-mono text-[10px]" style={{ color: 'var(--muted)' }}>
          {formatTime(msg.ts)}
        </div>
      </div>
    </div>
  )

  const badge = msg.mode ? MODE_BADGE[msg.mode] : null

  return (
    <div className="flex gap-3 mb-6 anim-msg-in">
      <div
        className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center font-display text-xs font-bold"
        style={{ background: 'linear-gradient(135deg, var(--accent), #4f46e5)', color: '#fff' }}
      >
        J
      </div>
      <div className="flex-1 min-w-0 max-w-[min(640px,90%)]">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="font-medium text-xs" style={{ color: 'var(--text-secondary)' }}>JARVIS</span>
          {badge && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-medium"
              style={{ color: badge.color, background: badge.bg }}>
              {badge.label}
            </span>
          )}
          <span className="font-mono text-[10px]" style={{ color: 'var(--muted)' }}>{formatTime(msg.ts)}</span>
        </div>
        <div className="group relative msg-assistant px-4 py-3 text-sm leading-relaxed" style={{ color: 'var(--text)' }}>
          {renderContent(msg.text)}
          {msg.streaming && !msg.text && <TypingDots />}
          {msg.streaming && msg.text && (
            <span className="inline-block w-1.5 h-4 rounded-sm ml-0.5 align-middle anim-blink"
              style={{ background: 'var(--accent-light)' }} />
          )}
          {!msg.streaming && msg.text && (
            <button onClick={copy}
              className="absolute top-2 right-2 font-mono text-[10px] px-2 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity btn-ghost"
              style={{ color: copied ? 'var(--green)' : 'var(--muted)' }}>
              {copied ? '✓' : 'Kopírovat'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function ChatPanel() {
  const [input, setInput] = useState('')
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
    if (file?.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (ev) => setPendingImage(ev.target?.result as string)
      reader.readAsDataURL(file)
    }
  }, [])

  const send = useCallback(() => {
    const t = input.trim()
    if ((!t && !pendingImage) || orbState === 'thinking') return
    const text = pendingImage ? `[OBRAZ:${pendingImage.substring(0, 100)}...] ${t}` : t
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
      style={dragOver ? { outline: '2px solid var(--accent)', outlineOffset: -2 } : undefined}
    >
      {/* Header */}
      <div className="flex items-center justify-between shrink-0 px-5 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <div>
          <h2 className="font-display text-sm font-semibold" style={{ color: 'var(--text)' }}>Chat</h2>
          <p className="text-[11px]" style={{ color: 'var(--muted)' }}>Copilot · Agent · Akce</p>
        </div>
        <button onClick={clearMsgs} className="btn-ghost px-3 py-1.5 text-xs font-mono">
          Vymazat
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <HeroPanel onSend={sendCmd} />
        ) : (
          <div className="max-w-3xl mx-auto px-5 pt-6 pb-4">
            {messages.map(m => <MessageBubble key={m.id} msg={m} />)}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="shrink-0 px-5 pb-5 pt-2 max-w-3xl w-full mx-auto flex flex-col gap-2">
        <div className="flex flex-wrap gap-1.5">
          {QUICK_ACTIONS.map(({ label, cmd }) => (
            <button
              key={label}
              type="button"
              onClick={() => sendCmd(cmd)}
              disabled={busy}
              className="status-pill hover:opacity-90 transition-opacity disabled:opacity-40"
              style={{ cursor: busy ? 'not-allowed' : 'pointer', color: 'var(--text-secondary)' }}
            >
              {label}
            </button>
          ))}
        </div>

        {pendingImage && (
          <div className="flex items-center gap-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={pendingImage} alt="pending" className="h-12 w-12 rounded-lg object-cover" style={{ border: '1px solid var(--border-accent)' }} />
            <button onClick={() => setPendingImage(null)} className="text-xs" style={{ color: 'var(--red)' }}>Odebrat</button>
          </div>
        )}

        {dragOver && (
          <p className="text-center text-xs font-mono" style={{ color: 'var(--accent-light)' }}>Pusť obrázek pro přiložení</p>
        )}

        {!input && (
          <div className="flex items-center gap-2 text-[11px]" style={{ color: 'var(--muted)' }}>
            <span>Zkuste:</span>
            <span className="status-pill" style={{ color: 'var(--accent-light)' }}>{pl.tag}</span>
          </div>
        )}

        <div className="input-shell flex gap-2 items-end px-3 py-2">
          <button
            type="button"
            onClick={toggleMic}
            disabled={busy}
            title={isMicActive ? 'Zastavit mikrofon' : 'Mluvit'}
            className="w-9 h-9 rounded-lg shrink-0 flex items-center justify-center btn-ghost"
            style={{
              color: isMicActive ? 'var(--red)' : 'var(--muted)',
              borderColor: isMicActive ? 'rgba(248,113,113,.3)' : undefined,
              background: isMicActive ? 'rgba(248,113,113,.1)' : undefined,
            }}
          >
            {Icons.mic}
          </button>
          <textarea
            ref={taRef}
            value={input}
            onChange={e => {
              setInput(e.target.value)
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
            }}
            onKeyDown={onKey}
            placeholder={pl.text}
            rows={1}
            disabled={busy}
            className="flex-1 bg-transparent border-none resize-none outline-none text-sm py-2"
            style={{ color: 'var(--text)', minHeight: 36, maxHeight: 140 }}
          />
          <button
            onClick={send}
            disabled={busy || (!input.trim() && !pendingImage)}
            className="btn-primary w-9 h-9 shrink-0 flex items-center justify-center"
            style={{ padding: 0 }}
          >
            {busy
              ? <div className="w-4 h-4 rounded-full anim-spin" style={{ border: '2px solid rgba(255,255,255,.3)', borderTopColor: '#fff' }} />
              : Icons.send
            }
          </button>
        </div>

        <p className="text-center font-mono text-[10px]" style={{ color: 'var(--muted)' }}>
          Enter odeslat · Shift+Enter nový řádek · ↑↓ historie
        </p>
      </div>
    </div>
  )
}
