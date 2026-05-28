import { useState, useRef, useEffect, useCallback } from 'react'
import { useJarvis } from '../store/jarvis'

function TypingDots() {
  return (
    <div className="typing-indicator">
      {[0,1,2].map(i => (
        <span key={i} className="typing-dot" style={{ animationDelay:`${i*0.18}s` }} />
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
          {lang && <span style={{ float:'right', fontSize:9, color:'var(--text2)', fontFamily:'var(--font-mono)' }}>{lang}</span>}
          {code}
        </pre>
      )
    }
    const chunks = p.split(/(`[^`]+`)/g)
    return (
      <span key={i}>
        {chunks.map((c, j) =>
          c.startsWith('`') ? <code key={j}>{c.slice(1,-1)}</code> : c
        )}
      </span>
    )
  })
}

function Message({ msg }) {
  const isUser = msg.sender === 'user'
  const t = new Date(msg.ts).toLocaleTimeString('cs', { hour:'2-digit', minute:'2-digit', second:'2-digit' })

  return (
    <div className={`msg-group ${isUser?'user':''} fade-up`}>
      <div className={`avatar-hud ${isUser?'u':'j'}`}>{isUser ? 'U' : 'J'}</div>
      <div className="msg-content">
        <div className="msg-meta">
          {isUser ? 'USER' : 'JARVIS'} · {t}
        </div>
        <div className={`bubble ${isUser?'u':'j'}`}>
          {renderContent(msg.text)}
          {msg.streaming && !msg.text && <TypingDots />}
          {msg.streaming && msg.text && (
            <span style={{ display:'inline-block', width:8, height:13, background:'var(--cyan)',
              marginLeft:2, verticalAlign:'middle', animation:'pulse 0.8s ease-in-out infinite',
              borderRadius:1, boxShadow:'0 0 6px var(--cyan)' }} />
          )}
        </div>
      </div>
    </div>
  )
}

function ConnBadge() {
  const connStatus = useJarvis(s => s.connStatus)
  const retry      = useJarvis(s => s.retry)
  const map = {
    connected:    { color:'var(--green)',  label:'CONNECTED' },
    connecting:   { color:'var(--amber)',  label:'CONNECTING' },
    disconnected: { color:'var(--red)',    label:'OFFLINE' },
    error:        { color:'var(--red)',    label:'ERROR' },
    failed:       { color:'var(--red)',    label:'FAILED' },
  }
  const { color, label } = map[connStatus] || map.disconnected
  return (
    <button onClick={retry} className="conn-badge" style={{
      color, borderColor:`${color}33`, background:`${color}0a`,
    }}>
      <span style={{ width:5, height:5, borderRadius:'50%', background:color,
        boxShadow:`0 0 6px ${color}`,
        animation: connStatus==='connecting' ? 'pulse 1s ease-in-out infinite' : 'none' }} />
      {label}
    </button>
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
  const [hist, setHist] = useState([])
  const [hidx, setHidx] = useState(-1)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:'smooth' }) }, [messages])

  const send = useCallback(() => {
    const t = input.trim()
    if (!t || orbState === 'thinking') return
    setHist(h => [t, ...h.slice(0,49)])
    setHidx(-1)
    setInput('')
    if (taRef.current) taRef.current.style.height = 'auto'
    sendCmd(t)
    taRef.current?.focus()
  }, [input, orbState, sendCmd])

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
    if (e.key === 'ArrowUp' && !input) {
      e.preventDefault()
      const n = Math.min(hidx+1, hist.length-1)
      setHidx(n); setInput(hist[n] || '')
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const n = Math.max(hidx-1,-1)
      setHidx(n); setInput(n===-1 ? '' : hist[n])
    }
  }

  const busy = orbState === 'thinking' || orbState === 'speaking'

  return (
    <>
      <div className="panel-header">
        <span className="panel-title">COMMUNICATION</span>
        <div style={{ display:'flex', gap:8 }}>
          <ConnBadge />
          <button onClick={clearMsgs} style={{
            fontFamily:'var(--font-hud)', fontSize:8, letterSpacing:'.1em',
            color:'var(--text2)', background:'none', border:'none', cursor:'pointer', padding:'2px 6px',
          }}>CLEAR</button>
        </div>
      </div>

      <div className="messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-logo">J</div>
            <div className="chat-empty-sub" style={{ letterSpacing:'.2em' }}>JARVIS ONLINE</div>
            <div style={{ fontFamily:'var(--font-mono)', fontSize:10, opacity:.4, marginTop:4 }}>
              ENTER COMMAND ↵
            </div>
          </div>
        ) : (
          messages.map(m => <Message key={m.id} msg={m} />)
        )}
        <div ref={bottomRef} />
      </div>

      <div className="input-area">
        <textarea
          ref={taRef}
          value={input}
          onChange={e => {
            setInput(e.target.value)
            e.target.style.height = 'auto'
            e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px'
          }}
          onKeyDown={onKey}
          placeholder="ENTER COMMAND..."
          rows={1}
          className="chat-input"
          disabled={busy}
        />
        <button onClick={send} disabled={busy || !input.trim()} className="send-btn">↵</button>
      </div>
    </>
  )
}
