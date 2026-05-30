import { useState, useRef, useEffect, useCallback } from 'react'
import { useJarvis } from '../store/jarvis'
import SystemPanel from './SystemPanel'
import AIOrb from './AIOrb'

// Každý placeholder ukazuje reálný příkaz který JARVIS umí — funguje jako feature discovery
const PLACEHOLDERS = [
  { text: 'Otevři Spotify…',             tag: 'ovládání PC' },
  { text: 'Počasí Praha…',               tag: 'Open-Meteo' },
  { text: 'Popiš obrazovku…',            tag: 'vision AI' },
  { text: 'Zahraj Bohemian Rhapsody…',   tag: 'YouTube' },
  { text: 'Jaké máš komponenty?',        tag: 'hardware' },
  { text: 'Screenshot…',                 tag: 'systém' },
  { text: 'Zavři Chrome…',               tag: 'procesy' },
  { text: 'Přelož hello world…',         tag: 'AI překlad' },
  { text: 'Vypočítej 15% z 2400…',       tag: 'kalkulačka' },
  { text: 'Zapamatuj si…',               tag: 'paměť' },
]

const SUGGESTIONS = [
  'kolik je hodin?', 'počasí Praha', 'info o systému', 'screenshot', 'hardware info',
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
          {lang && <span style={{ float: 'right', fontSize: 8, color: 'var(--text2)', fontFamily: 'var(--font-mono)' }}>{lang}</span>}
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
    setTimeout(() => setCopied(false), 1400)
  }

  if (isUser) {
    return (
      <div style={{
        display: 'flex', justifyContent: 'flex-end',
        marginBottom: 20, gap: 10, alignItems: 'flex-end',
      }}>
        <div style={{ maxWidth: 580 }}>
          <div style={{
            padding: '10px 16px',
            background: 'linear-gradient(135deg, rgba(59,130,246,.18), rgba(99,102,241,.14))',
            border: '1px solid rgba(99,102,241,.25)',
            borderRadius: '16px 16px 4px 16px',
            fontSize: 14, lineHeight: 1.65, color: 'var(--text)',
            boxShadow: '0 2px 12px rgba(59,130,246,.1)',
          }}>
            {renderContent(msg.text)}
          </div>
          <div style={{
            textAlign: 'right', marginTop: 4,
            fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text3)',
          }}>
            {formatTime(msg.ts)}
          </div>
        </div>
        {/* User avatar */}
        <div style={{
          width: 30, height: 30, borderRadius: 8, flexShrink: 0,
          background: 'linear-gradient(135deg, rgba(59,130,246,.18), rgba(99,102,241,.12))',
          border: '1px solid rgba(99,102,241,.25)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'var(--font-hud)', fontSize: 10, fontWeight: 700,
          color: '#93c5fd',
        }}>U</div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', gap: 12, marginBottom: 24, alignItems: 'flex-start' }}>
      {/* JARVIS avatar */}
      <div style={{
        width: 30, height: 30, borderRadius: 8, flexShrink: 0, marginTop: 1,
        background: 'linear-gradient(135deg, rgba(0,200,255,.12), rgba(99,102,241,.08))',
        border: '1px solid rgba(0,200,255,.2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: 'var(--font-hud)', fontSize: 10, fontWeight: 700,
        color: 'var(--cyan)', boxShadow: '0 0 12px rgba(0,200,255,.08)',
      }}>J</div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {/* Name + time */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 7, marginBottom: 6,
          fontFamily: 'var(--font-mono)', fontSize: 10,
        }}>
          <span style={{ color: 'rgba(0,200,255,.7)', letterSpacing: '.06em', fontWeight: 600 }}>JARVIS</span>
          <span style={{ color: 'var(--text3)' }}>·</span>
          <span style={{ color: 'var(--text3)' }}>{formatTime(msg.ts)}</span>
        </div>

        {/* Content */}
        <div style={{ position: 'relative' }}>
          <div style={{
            fontSize: 14, lineHeight: 1.75, color: 'rgba(219,234,254,.9)',
            position: 'relative',
          }}>
            {renderContent(msg.text)}
            {msg.streaming && !msg.text && <TypingDots />}
            {msg.streaming && msg.text && <span className="cursor-blink" />}
          </div>

          {!msg.streaming && msg.text && (
            <button onClick={copy} style={{
              position: 'absolute', top: -2, right: 0,
              background: copied ? 'rgba(34,211,165,.1)' : 'rgba(0,0,0,.4)',
              border: `1px solid ${copied ? 'rgba(34,211,165,.3)' : 'rgba(255,255,255,.08)'}`,
              borderRadius: 5, color: copied ? 'var(--green)' : 'var(--text2)',
              cursor: 'pointer', fontSize: 10, padding: '2px 8px',
              fontFamily: 'var(--font-mono)',
              opacity: 0, transition: 'opacity .15s, background .15s',
            }}
              className="copy-btn"
              onMouseEnter={e => e.currentTarget.style.opacity = '1'}
            >
              {copied ? '✓' : '⎘'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function ChatPanel({ orbGlow, orbState }) {
  const [input, setInput]       = useState('')
  const [showRight, setShowRight] = useState(false)
  const messages  = useJarvis(s => s.messages)
  const sendCmd   = useJarvis(s => s.sendCommand)
  const clearMsgs = useJarvis(s => s.clearMessages)
  const bottomRef = useRef()
  const taRef     = useRef()
  const [hist, setHist]   = useState([])
  const [hidx, setHidx]   = useState(-1)
  const [plIdx, setPlIdx] = useState(0)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => {
    const t = setInterval(() => setPlIdx(i => (i + 1) % PLACEHOLDERS.length), 3200)
    return () => clearInterval(t)
  }, [])

  const send = useCallback(() => {
    const t = input.trim()
    if (!t || orbState === 'thinking') return
    setHist(h => [t, ...h.slice(0, 49)])
    setHidx(-1); setInput('')
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
    <div style={{ display: 'flex', width: '100%', height: '100%', overflow: 'hidden' }}>

      {/* ── Main chat area ── */}
      <div style={{
        flex: 1, display: 'flex', flexDirection: 'column',
        alignItems: 'center', overflow: 'hidden',
      }}>

        {/* Toolbar */}
        <div style={{
          width: '100%', maxWidth: 760,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '10px 16px 6px',
          borderBottom: '1px solid var(--border2)',
          flexShrink: 0,
        }}>
          <span className="panel-title">CHAT</span>
          <div style={{ display: 'flex', gap: 6 }}>
            <button onClick={() => setShowRight(r => !r)} style={{
              fontFamily: 'var(--font-mono)', fontSize: 9,
              color: showRight ? 'var(--cyan)' : 'var(--text2)',
              background: showRight ? 'rgba(0,200,255,.07)' : 'none',
              border: `1px solid ${showRight ? 'rgba(0,200,255,.2)' : 'transparent'}`,
              borderRadius: 5, cursor: 'pointer', padding: '2px 8px',
              transition: 'all .18s',
            }}>
              METRIKY
            </button>
            <button onClick={clearMsgs} style={{
              fontFamily: 'var(--font-mono)', fontSize: 9,
              color: 'var(--text2)', background: 'none', border: 'none',
              cursor: 'pointer', padding: '2px 8px', borderRadius: 5,
              transition: 'color .15s',
            }}
              onMouseEnter={e => e.currentTarget.style.color = 'var(--red)'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--text2)'}
            >CLEAR</button>
          </div>
        </div>

        {/* Messages */}
        <div style={{
          flex: 1, overflowY: 'auto', width: '100%',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
        }}>
          {messages.length === 0 ? (
            /* Empty state — vertically centered */
            <div style={{
              flex: 1, display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', gap: 10,
              padding: 32, pointerEvents: 'none',
            }}>
              <div style={{
                width: 72, height: 72, borderRadius: 20,
                background: 'linear-gradient(135deg, rgba(0,200,255,.1), rgba(99,102,241,.07))',
                border: '1px solid rgba(0,200,255,.18)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: 'var(--font-hud)', fontSize: 26, fontWeight: 900,
                color: 'var(--cyan)', boxShadow: '0 0 40px rgba(0,200,255,.1)',
                animation: 'breathe 4s ease-in-out infinite',
              }}>J</div>
              <div style={{
                fontFamily: 'var(--font-hud)', fontSize: 16, fontWeight: 700,
                color: 'rgba(0,200,255,.45)', letterSpacing: '.25em',
              }}>JARVIS</div>
              <div style={{
                fontFamily: 'var(--font-ui)', fontSize: 13,
                color: 'var(--text2)', marginTop: 2,
              }}>Jak ti mohu pomoct?</div>
            </div>
          ) : (
            /* Messages — push to bottom when few */
            <div style={{
              width: '100%', maxWidth: 760,
              display: 'flex', flexDirection: 'column',
              justifyContent: 'flex-end',
              minHeight: '100%',
              padding: '24px 20px 8px',
            }}>
              {messages.map(m => <Message key={m.id} msg={m} />)}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Suggestions */}
        {messages.length === 0 && (
          <div style={{
            width: '100%', maxWidth: 760,
            display: 'flex', flexWrap: 'wrap', gap: 6, padding: '0 16px 10px',
          }}>
            {SUGGESTIONS.map(s => (
              <button key={s} className="suggestion-chip" onClick={() => sendCmd(s)}>{s}</button>
            ))}
          </div>
        )}

        {/* Input */}
        <div style={{
          width: '100%', maxWidth: 760,
          padding: '8px 16px 14px',
          flexShrink: 0,
        }}>
          {/* Feature tag — ukazuje kategorii aktuálního placeholderu */}
          {!input && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6,
              marginBottom: 8, paddingLeft: 2,
            }}>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 9,
                color: 'var(--text3)', letterSpacing: '.04em',
              }}>
                JARVIS umí:
              </span>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 9,
                padding: '2px 8px', borderRadius: 10,
                background: 'rgba(78,205,196,.08)',
                border: '1px solid rgba(78,205,196,.2)',
                color: '#4ecdc4',
                letterSpacing: '.04em',
                transition: 'all .3s',
                key: plIdx,
              }}>
                {PLACEHOLDERS[plIdx].tag}
              </span>
            </div>
          )}

          <div style={{
            display: 'flex', gap: 8, alignItems: 'flex-end',
            background: 'rgba(6,12,26,.85)',
            border: '1px solid rgba(0,200,255,.16)',
            borderRadius: 14,
            padding: '6px 6px 6px 14px',
            boxShadow: '0 4px 24px rgba(0,0,0,.35)',
            transition: 'border-color .2s, box-shadow .2s',
          }}
            onFocusCapture={e => {
              e.currentTarget.style.borderColor = 'rgba(78,205,196,.35)'
              e.currentTarget.style.boxShadow = '0 4px 24px rgba(0,0,0,.35), 0 0 0 3px rgba(78,205,196,.05)'
            }}
            onBlurCapture={e => {
              e.currentTarget.style.borderColor = 'rgba(0,200,255,.16)'
              e.currentTarget.style.boxShadow = '0 4px 24px rgba(0,0,0,.35)'
            }}
          >
            <textarea
              ref={taRef}
              value={input}
              onChange={e => {
                setInput(e.target.value)
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
              }}
              onKeyDown={onKey}
              placeholder={PLACEHOLDERS[plIdx].text}
              rows={1}
              style={{
                flex: 1, background: 'transparent', border: 'none',
                color: 'var(--text)', fontSize: 14,
                fontFamily: 'var(--font-ui)', resize: 'none', outline: 'none',
                minHeight: 36, maxHeight: 160, lineHeight: 1.55, padding: '6px 0',
              }}
              disabled={busy}
            />
            <button onClick={send} disabled={busy || !input.trim()} style={{
              width: 38, height: 38, flexShrink: 0,
              background: input.trim() && !busy
                ? 'linear-gradient(135deg, #4ecdc4, #0066ff)'
                : 'rgba(255,255,255,.04)',
              border: 'none', borderRadius: 10,
              color: input.trim() && !busy ? '#fff' : 'var(--text2)',
              cursor: input.trim() && !busy ? 'pointer' : 'not-allowed',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all .2s',
              boxShadow: input.trim() && !busy ? '0 0 18px rgba(78,205,196,.35)' : 'none',
            }}>
              {busy ? (
                <div style={{ width: 14, height: 14, border: '2px solid var(--text2)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin .8s linear infinite' }} />
              ) : (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
                  style={{ width: 15, height: 15 }}>
                  <line x1="22" y1="2" x2="11" y2="13"/>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
              )}
            </button>
          </div>

          <div style={{
            textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 9,
            color: 'var(--text3)', marginTop: 6, letterSpacing: '.05em',
          }}>
            ↵ odeslat · ⇧↵ nový řádek · ↑↓ historie
          </div>
        </div>
      </div>

      {/* ── Right panel: orb + metrics (collapsible) ── */}
      {showRight && (
        <div style={{
          width: 240, flexShrink: 0,
          borderLeft: '1px solid var(--border2)',
          display: 'flex', flexDirection: 'column', gap: 8,
          padding: 10, overflowY: 'auto',
        }}>
          {/* Orb */}
          <div className="panel orb-panel" style={{
            boxShadow: `var(--card-shadow), 0 0 30px ${orbGlow || 'rgba(0,200,255,.1)'}`,
            transition: 'box-shadow 1.2s ease',
          }}>
            <AIOrb size={180} />
            <div style={{
              fontFamily: 'var(--font-hud)', fontSize: 8, letterSpacing: '.18em',
              marginTop: 10, transition: 'color .4s',
              color: { idle: 'var(--text2)', listening: 'var(--cyan)', thinking: 'var(--purple)', speaking: 'var(--green)' }[orbState],
            }}>
              {{ idle: '○ IDLE', listening: '◉ LISTENING', thinking: '◎ PROCESSING', speaking: '● SPEAKING' }[orbState]}
            </div>
          </div>

          {/* Metrics */}
          <div style={{ flex: 1, minHeight: 0 }}>
            <SystemPanel compact />
          </div>
        </div>
      )}
    </div>
  )
}
