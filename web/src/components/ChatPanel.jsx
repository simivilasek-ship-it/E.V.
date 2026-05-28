import { useState, useRef, useEffect } from 'react'
import { useJarvis } from '../store/jarvis'

function Message({ msg }) {
  const isUser = msg.sender === 'user'
  const isCode = msg.text.includes('```')

  const renderText = (text) => {
    const parts = text.split(/(```[\s\S]*?```)/g)
    return parts.map((p, i) => {
      if (p.startsWith('```')) {
        const code = p.replace(/^```\w*\n?/, '').replace(/```$/, '')
        return (
          <pre key={i} className="mt-2 p-3 rounded text-xs overflow-x-auto"
            style={{ background: '#050a15', color: '#60c8f8', border: '1px solid #1a3050' }}>
            {code}
          </pre>
        )
      }
      return <span key={i}>{p}</span>
    })
  }

  return (
    <div className={`flex fade-in mb-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className="max-w-xs lg:max-w-md">
        <div className="text-xs mb-1 px-1" style={{ color: '#4a6080' }}>
          {isUser ? 'ty' : 'jarvis'} · {new Date(msg.ts).toLocaleTimeString('cs', { hour:'2-digit', minute:'2-digit' })}
        </div>
        <div className="rounded-lg px-4 py-2 text-sm leading-relaxed"
          style={{
            background: isUser ? 'rgba(0,212,255,0.08)' : 'rgba(11,18,32,0.8)',
            border: `1px solid ${isUser ? 'rgba(0,212,255,0.25)' : '#1a3050'}`,
            color: '#e2f0ff',
          }}>
          {renderText(msg.text)}
        </div>
      </div>
    </div>
  )
}

export default function ChatPanel() {
  const [input, setInput] = useState('')
  const messages   = useJarvis(s => s.messages)
  const sendCommand= useJarvis(s => s.sendCommand)
  const clearMsgs  = useJarvis(s => s.clearMessages)
  const orbState   = useJarvis(s => s.orbState)
  const bottomRef  = useRef()

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const handleSend = () => {
    if (!input.trim()) return
    sendCommand(input)
    setInput('')
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  return (
    <div className="flex flex-col h-full glass rounded-xl" style={{ minHeight: 0 }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: '#1a3050' }}>
        <span className="text-xs tracking-widest" style={{ color: '#4a6080' }}>KOMUNIKACE</span>
        <button onClick={clearMsgs} className="text-xs px-2 py-1 rounded"
          style={{ color: '#4a6080', border: '1px solid #1a3050' }}
          onMouseEnter={e => e.target.style.color = '#00d4ff'}
          onMouseLeave={e => e.target.style.color = '#4a6080'}>
          🗑 clear
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3" style={{ minHeight: 0 }}>
        {messages.length === 0 && (
          <div className="text-center mt-8 text-xs" style={{ color: '#4a6080' }}>
            JARVIS čeká na příkaz...
          </div>
        )}
        {messages.map(m => <Message key={m.id} msg={m} />)}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t" style={{ borderColor: '#1a3050' }}>
        <div className="flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Napiš příkaz nebo otázku..."
            className="flex-1 px-3 py-2 rounded-lg text-sm outline-none"
            style={{
              background: '#050a15', color: '#e2f0ff',
              border: '1px solid #1a3050', fontFamily: 'Courier New',
            }}
            disabled={orbState === 'thinking'}
          />
          <button onClick={handleSend}
            className="px-4 py-2 rounded-lg text-sm font-mono transition-all"
            style={{
              background: orbState === 'thinking' ? '#1a3050' : '#0099bb',
              color: orbState === 'thinking' ? '#4a6080' : '#e2f0ff',
              cursor: orbState === 'thinking' ? 'not-allowed' : 'pointer',
            }}>
            ↵
          </button>
        </div>
        <div className="mt-1 text-xs" style={{ color: '#4a6080' }}>
          Enter = odeslat · Shift+Enter = nový řádek
        </div>
      </div>
    </div>
  )
}
