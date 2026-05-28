import { useState, useRef, useEffect, useCallback } from 'react'
import { useJarvis } from '../store/jarvis'

function TypingDots() {
  return (
    <span style={{ display:'inline-flex', gap:3, alignItems:'center', marginLeft:4 }}>
      {[0,1,2].map(i => (
        <span key={i} className="typing-dot" style={{ animationDelay:`${i*0.18}s` }} />
      ))}
    </span>
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
          {lang && <span style={{ color:'#3a5a78', fontSize:10, float:'right' }}>{lang}</span>}
          {code}
        </pre>
      )
    }
    return p.split(/(`[^`]+`)/g).map((chunk, j) =>
      chunk.startsWith('`') ? <code key={j}>{chunk.slice(1,-1)}</code> : <span key={j}>{chunk}</span>
    )
  })
}

function Message({ msg }) {
  const isUser = msg.sender === 'user'
  const t = new Date(msg.ts).toLocaleTimeString('cs', { hour:'2-digit', minute:'2-digit' })

  return (
    <div className={`msg ${isUser?'user':''}`}>
      <div className={`avatar ${isUser?'u':'j'}`}>{isUser ? 'U' : 'J'}</div>
      <div>
        <div style={{ fontSize:10, color:'#3a5a78', marginBottom:4, textAlign: isUser?'right':'left' }}>
          {isUser?'ty':'jarvis'} · {t}
        </div>
        <div className={`bubble ${isUser?'u':'j'}`}>
          {renderContent(msg.text)}
          {msg.streaming && <TypingDots />}
        </div>
      </div>
    </div>
  )
}

function ConnBadge() {
  const { connStatus, connect } = useJarvis(s => ({ connStatus: s.connStatus, connect: s.connect }))
  const map = {
    connected:    { color:'#00e676', label:'● live' },
    connecting:   { color:'#fbbf24', label:'◎ connecting...' },
    disconnected: { color:'#ef4444', label:'○ offline' },
    error:        { color:'#ef4444', label:'✕ error' },
  }
  const { color, label } = map[connStatus] || map.disconnected
  return (
    <button onClick={connect} style={{
      fontSize:10, padding:'2px 8px', borderRadius:20,
      color, border:`1px solid ${color}33`, background:'transparent', cursor:'pointer',
    }}>{label}</button>
  )
}

export default function ChatPanel() {
  const [input, setInput]     = useState('')
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
    taRef.current.style.height = 'auto'
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
      {/* Header */}
      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between',
        padding:'10px 16px', borderBottom:'1px solid rgba(0,212,255,.08)', flexShrink:0 }}>
        <span style={{ fontSize:10, letterSpacing:'.12em', color:'#3a5a78' }}>KOMUNIKACE</span>
        <div style={{ display:'flex', gap:8 }}>
          <ConnBadge />
          <button onClick={clearMsgs} style={{ fontSize:11, color:'#3a5a78', background:'none', border:'none', cursor:'pointer' }}>🗑</button>
        </div>
      </div>

      {/* Messages */}
      <div className="messages">
        {messages.length === 0 && (
          <div style={{ display:'flex', flexDirection:'column', alignItems:'center',
            justifyContent:'center', height:'100%', color:'#3a5a78', textAlign:'center' }}>
            <div style={{ fontSize:40, opacity:.1, marginBottom:12 }}>J</div>
            <div style={{ fontSize:12 }}>JARVIS čeká na příkaz</div>
            <div style={{ fontSize:11, opacity:.5, marginTop:4 }}>Enter = odeslat · ↑↓ = historie</div>
          </div>
        )}
        {messages.map(m => <Message key={m.id} msg={m} />)}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="input-area">
        <textarea
          ref={taRef}
          value={input}
          onChange={e => {
            setInput(e.target.value)
            e.target.style.height = 'auto'
            e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
          }}
          onKeyDown={onKey}
          placeholder="Napiš příkaz... (Enter = odeslat, Shift+Enter = nový řádek)"
          rows={1}
          className="chat-input"
          disabled={busy}
        />
        <button onClick={send} disabled={busy || !input.trim()} className="send-btn">↵</button>
      </div>
    </>
  )
}
