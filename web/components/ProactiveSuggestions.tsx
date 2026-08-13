'use client'
import { useEffect, useState } from 'react'
import { useEV } from '@/store/ev'

export default function ProactiveSuggestions() {
  const [suggestions, setSuggestions] = useState<string[]>([])
  const sendCmd = useEV(s => s.sendCommand)
  
  useEffect(() => {
    const poll = async () => {
      try {
        const r = await fetch('/api/proactive/suggestions')
        const d = await r.json()
        if (d.ok && d.suggestions?.length) setSuggestions(d.suggestions)
        else setSuggestions([])
      } catch { setSuggestions([]) }
    }
    poll()
    const t = setInterval(poll, 30000) // každých 30s
    return () => clearInterval(t)
  }, [])
  
  if (!suggestions.length) return null
  
  return (
    <div className="mx-5 mb-3 flex flex-col gap-1.5">
      {suggestions.map((s, i) => (
        <button
          key={i}
          onClick={() => sendCmd(s.replace(/^[🔥⚠️💡🌙🌅]/u, '').trim())}
          className="text-left px-3 py-2 rounded-lg text-xs transition-all hover:opacity-90"
          style={{
            background: 'rgba(99,102,241,.08)',
            border: '1px solid rgba(99,102,241,.15)',
            color: 'var(--text-secondary)',
          }}
        >
          {s}
        </button>
      ))}
    </div>
  )
}
