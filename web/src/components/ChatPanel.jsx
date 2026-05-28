import { useState, useRef, useEffect, useCallback } from 'react'
import { useJarvis } from '../store/jarvis'

function TypingDots() {
  return (
    <span className="inline-flex gap-1 items-center ml-1">
      {[0,1,2].map(i => (
        <span key={i} className="w-1 h-1 rounded-full"
          style={{
            background: '#00d4ff',
            animation: `bounce 1.2s ${i*0.2}s ease-in-out infinite`,
          }} />
      ))}
    </span>
  )
}

function Message({ msg }) {
  const isUser = msg.sender === 'user'
  const isJarvis = msg.sender === 'jarvis'

  const renderText = (text) => {
    if (!text) return null
    const parts = text.split(/(```[\s\S]*?```)/g)
    return parts.map((p, i) => {
      if (p.startsWith('```')) {
        const lang = p.match(/^```(\w*)/)?.[1] || ''
        const code = p.replace(/^```\w*\n?/, '').replace(/```$/, '').trim()
        return (
          <pre key={i} className="mt-2 p-3 rounded text-xs overflow-x-auto relative"
            style={{ background: '#050a15', color: '#60c8f8', border: '1px solid #1a3050', fontFamily: 'Courier New' }}>
            {lang && <span className="absolute top-1 right-2 text-xs" style={{ color: '#4a6080' }}>{lang}</span>}
            {code}
          </pre>
        )
      }
      // Inline bold **text**
      const formatted = p.split(/(\*\*[^*]+\*\*)/g).map((chunk, j) =>
        chunk.startsWith('**') ? <strong key={j}>{chunk.slice(2, -2)}</strong> : chunk
      )
      return <span key={i}>{formatted}</span>
    })
  }

  const time = new Date(msg.ts).toLocaleTimeString('cs', { hour: '2-digit', minute: '2-digit' })

  return (
    <div className={`flex mb-4 fade-in ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* Avatar */}
      {isJarvis && (
        <div className="w-7 h-7 rounded-full border flex-shrink-0 flex items-center justify-center text-xs mr-2 mt-1"
          style={{ borderColor: 'rgba(0,212,255,0.4)', color: '#00d4ff', background: 'rgba(0,212,255,0.06)' }}>
          J
        </div>
      )}

      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`} style={{ maxWidth: '75%' }}>
        <div className="text-xs mb-1 px-1" style={{ color: '#4a6080' }}>
          {isUser ? 'ty' : 'jarvis'} · {time}
        </div>
        <div className="rounded-xl px-4 py-2.5 text-sm leading-relaxed"
          style={{
            background: isUser
              ? 'linear-gradient(135deg, rgba(0,153,187,0.15), rgba(0,212,255,0.08))'
              : 'rgba(11,18,32,0.85)',
            border: `1px solid ${isUser ? 'rgba(0,212,255,0.25)' : '#1a3050'}`,
            color: '#e2f0ff',
            boxShadow: isUser ? '0 0 12px rgba(0,212,255,0.06)' : 'none',
          }}>
          {renderText(msg.text)}
          {msg.streaming && <TypingDots />}
        </div>
        {msg.error && (
          <div className="text-xs mt-1 px-2 py-1 rounded" style={{ color: '#ff5252', background: 'rgba(255,82,82,0.08)' }}>
            Chyba odpovědi
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-7 h-7 rounded-full border flex-shrink-0 flex items-center justify-center text-xs ml-2 mt-1"
          style={{ borderColor: '#1a3050', color: '#7ea8d4', background: '#0b1220' }}>
          U
        </div>
      )}
    </div>
  )
}

function ConnectionBadge() {
  const { isConnected, connStatus, connect } = useJarvis(s => ({
    isConnected: s.isConnected, connStatus: s.connStatus, connect: s.connect,
  }))
  const colors = { connected: '#00e676', connecting: '#fbbf24', disconnected: '#ff5252', error: '#ff5252' }
  const labels = { connected: '● live', connecting: '◎ spojuji...', disconnected: '○ offline', error: '✕ chyba' }
  return (
    <button onClick={connect} title="Klikni pro opakované připojení"
      className="text-xs px-2 py-0.5 rounded transition-all"
      style={{ color: colors[connStatus] || '#4a6080', border: `1px solid ${colors[connStatus]}22` }}>
      {labels[connStatus] || '○ offline'}
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
  const textareaRef = useRef()
  const [history, setHistory] = useState([])
  const [histIdx, setHistIdx] = useState(-1)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = useCallback(() => {
    const text = input.trim()
    if (!text || orbState === 'thinking') return
    setHistory(h => [text, ...h.slice(0, 49)])
    setHistIdx(-1)
    setInput('')
    sendCmd(text)
    textareaRef.current?.focus()
  }, [input, orbState, sendCmd])

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
    // History navigation
    if (e.key === 'ArrowUp' && input === '') {
      e.preventDefault()
      const next = Math.min(histIdx + 1, history.length - 1)
      setHistIdx(next)
      setInput(history[next] || '')
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const next = Math.max(histIdx - 1, -1)
      setHistIdx(next)
      setInput(next === -1 ? '' : history[next])
    }
  }

  const busy = orbState === 'thinking' || orbState === 'speaking'

  return (
    <div className="flex flex-col h-full glass rounded-xl" style={{ minHeight: 0 }}>
      <style>{`
        @keyframes bounce {
          0%, 100% { transform: translateY(0); opacity: 0.4; }
          50%       { transform: translateY(-4px); opacity: 1; }
        }
      `}</style>

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b flex-shrink-0"
        style={{ borderColor: '#1a3050' }}>
        <span className="text-xs tracking-widest" style={{ color: '#4a6080' }}>KOMUNIKACE</span>
        <div className="flex items-center gap-2">
          <ConnectionBadge />
          <button onClick={clearMsgs}
            className="text-xs px-2 py-0.5 rounded transition-all"
            style={{ color: '#4a6080', border: '1px solid #1a3050' }}
            onMouseEnter={e => e.target.style.color='#00d4ff'}
            onMouseLeave={e => e.target.style.color='#4a6080'}>
            🗑
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4" style={{ minHeight: 0 }}>
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center" style={{ color: '#4a6080' }}>
            <div className="text-4xl mb-3 opacity-20">J</div>
            <div className="text-xs">JARVIS čeká na příkaz...</div>
            <div className="text-xs mt-1 opacity-60">Enter = odeslat · ↑↓ = historie</div>
          </div>
        )}
        {messages.map(m => <Message key={m.id} msg={m} />)}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t flex-shrink-0" style={{ borderColor: '#1a3050' }}>
        <div className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => {
              setInput(e.target.value)
              // Auto-resize
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
            }}
            onKeyDown={handleKey}
            placeholder="Napiš příkaz... (Enter = odeslat, Shift+Enter = nový řádek, ↑ = historie)"
            rows={1}
            className="flex-1 px-3 py-2.5 rounded-lg text-sm outline-none resize-none"
            style={{
              background: '#050a15', color: '#e2f0ff',
              border: `1px solid ${busy ? '#1a3050' : 'rgba(0,212,255,0.2)'}`,
              fontFamily: 'inherit', minHeight: 42, maxHeight: 160,
              transition: 'border-color 0.2s',
              lineHeight: 1.5,
            }}
            disabled={busy}
          />
          <button onClick={handleSend} disabled={busy || !input.trim()}
            className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center text-lg transition-all"
            style={{
              background: busy || !input.trim() ? '#1a3050' : 'rgba(0,153,187,0.3)',
              color: busy || !input.trim() ? '#4a6080' : '#00d4ff',
              border: `1px solid ${busy || !input.trim() ? '#1a3050' : 'rgba(0,212,255,0.3)'}`,
              cursor: busy || !input.trim() ? 'not-allowed' : 'pointer',
              boxShadow: (!busy && input.trim()) ? '0 0 12px rgba(0,212,255,0.15)' : 'none',
            }}>
            ↵
          </button>
        </div>
      </div>
    </div>
  )
}
