import { useState, useRef, useEffect, useCallback } from 'react'
import { useJarvis } from '../store/jarvis'

const PLACEHOLDERS = [
  'Zadej příkaz nebo otázku…',
  'Otevři Spotify…',
  'Počasí Praha…',
  'Popiš obrazovku…',
  'Zahraj něco…',
  'Hardware info…',
]

const SUGGESTIONS = [
  'kolik je hodin?', 'počasí Praha', 'info o systému',
  'screenshot', 'hardware info',
]

function formatTime(ts) {
  const diff = (Date.now() - ts) / 1000
  if (diff < 60)   return 'právě teď'
  if (diff < 3600) return `před ${Math.floor(diff / 60)} min`
  return new Date(ts).toLocaleTimeString('cs', { hour: '2-digit', minute: '2-digit' })
}

function TypingDots() {
  return (
    <div className="typing-indicator">
      {[0, 1, 2].map(i => (
        <span key={i} className="typing-dot" style={{ animationDelay: `${i * 0.16}s` }} />
      ))}
    </div>
  )
}

function renderContent(text) {
  if (!text) return null
  const parts = text.split(/(```[\s\S]*?```)/g)
  return parts.map((p, i) => {
    if (p.startsWith('```')) {
      const lang = p.match(/^```(\w+)/)?.[1] || ''
      const code = p.replace(/^```\w*\n?/, '').replace(/\n?```$/, '')
      return (
        <pre key={i}>
          {lang && <span style={{ float: 'right', fontSize: 8, color: 'var(--text2)', fontFamily: 'var(--font-mono)', marginBottom: 4 }}>{lang}</span>}
          {code}
        </pre>
      )
    }
    return (
      <span key={i}>
        {p.split(/(`[^`]+`)/g).map((c, j) =>
          c.startsWith('`') ? <code key={j}>{c.slice(1, -1)}</code> : c
        )}
      </span>
    )
  })
}

function Message({ msg }) {
  const isUser = msg.sender === 'user'
  const [copied, setCopied] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(msg.text || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className={`msg-group ${isUser ? 'user' : ''}`}>
      <div className={`avatar ${isUser ? 'u' : 'j'}`}>
        {isUser ? 'U' : 'J'}
      </div>
      <div className="msg-content">
        <div className="msg-meta">
          <span className="msg-meta-name">{isUser ? 'USER' : 'JARVIS'}</span>
          <span>·</span>
          <span>{formatTime(msg.ts)}</span>
        </div>
        <div className={`bubble ${isUser ? 'u' : 'j'}`}>
          {renderContent(msg.text)}
          {msg.streaming && !msg.text && <TypingDots />}
          {msg.streaming && msg.text && <span className="cursor-blink" />}
          {!isUser && !msg.streaming && msg.text && (
            <button className="copy-btn" onClick={copy}>
              {copied ? '✓' : '⎘'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function ChatPanel() {
  const [input, setInput]   = useState('')
  const messages  = useJarvis(s => s.messages)
  const sendCmd   = useJarvis(s => s.sendCommand)
  const clearMsgs = useJarvis(s => s.clearMessages)
  const orbState  = useJarvis(s => s.orbState)
  const bottomRef = useRef()
  const taRef     = useRef()
  const [hist, setHist]   = useState([])
  const [hidx, setHidx]   = useState(-1)
  const [plIdx, setPlIdx] = useState(0)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const t = setInterval(() => setPlIdx(i => (i + 1) % PLACEHOLDERS.length), 3200)
    return () => clearInterval(t)
  }, [])

  const send = useCallback(() => {
    const t = input.trim()
    if (!t || orbState === 'thinking') return
    setHist(h => [t, ...h.slice(0, 49)])
    setHidx(-1)
    setInput('')
    if (taRef.current) taRef.current.style.height = 'auto'
    sendCmd(t)
    taRef.current?.focus()
  }, [input, orbState, sendCmd])

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); return }
    if (e.key === 'ArrowUp' && !input) {
      e.preventDefault()
      const n = Math.min(hidx + 1, hist.length - 1)
      setHidx(n); setInput(hist[n] || '')
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const n = Math.max(hidx - 1, -1)
      setHidx(n); setInput(n === -1 ? '' : hist[n])
    }
  }

  const busy = orbState === 'thinking' || orbState === 'speaking'

  return (
    <>
      {/* Header */}
      <div className="panel-header">
        <span className="panel-title">COMMUNICATION</span>
        <button onClick={clearMsgs} style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, letterSpacing: '.1em',
          color: 'var(--text2)', background: 'none', border: 'none',
          cursor: 'pointer', padding: '2px 6px', borderRadius: 4,
          transition: 'color .15s',
        }}
          onMouseEnter={e => e.target.style.color = 'var(--red)'}
          onMouseLeave={e => e.target.style.color = 'var(--text2)'}
        >
          CLEAR
        </button>
      </div>

      {/* Messages */}
      <div className="messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="empty-logo">J</div>
            <div className="empty-tagline">JARVIS ONLINE</div>
            <div className="empty-hint">ENTER COMMAND ↵</div>
          </div>
        ) : (
          messages.map(m => <Message key={m.id} msg={m} />)
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions */}
      {messages.length === 0 && (
        <div className="suggestions">
          {SUGGESTIONS.map(s => (
            <button key={s} className="suggestion-chip" onClick={() => sendCmd(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="input-area">
        <textarea
          ref={taRef}
          value={input}
          onChange={e => {
            setInput(e.target.value)
            e.target.style.height = 'auto'
            e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
          }}
          onKeyDown={onKey}
          placeholder={PLACEHOLDERS[plIdx]}
          rows={1}
          className="chat-input"
          disabled={busy}
        />
        <button onClick={send} disabled={busy || !input.trim()} className="send-btn">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
            style={{ width: 16, height: 16 }}>
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </>
  )
}
