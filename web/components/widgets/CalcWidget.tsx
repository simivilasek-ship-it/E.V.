'use client'
import { useEffect, useState } from 'react'

function safeEval(expr: string): string {
  const clean = expr
    .replace(/[^0-9+\-*/().%, ]/g, '')
    .replace(/(\d+)\s*%\s*(\d+)/g, '($1/100*$2)')  // 15% z 200
    .replace(/(\d+(?:\.\d+)?)\s*%/g, '($1/100)')
  try {
    // eslint-disable-next-line no-new-func
    const result = Function('"use strict"; return (' + clean + ')')()
    if (typeof result === 'number' && isFinite(result)) {
      return Number.isInteger(result) ? String(result) : result.toFixed(10).replace(/\.?0+$/, '')
    }
  } catch {}
  return '?'
}

export default function CalcWidget({ query }: { query: string }) {
  const [result, setResult] = useState('')
  const [expr, setExpr] = useState('')

  useEffect(() => {
    const raw = query
      .replace(/^(vypočítej|spočítej|kolik\s+je|calculate|calc)\s*/i, '')
      .replace(/,/g, '.').trim()
    setExpr(raw)
    setResult(raw ? safeEval(raw) : '')
  }, [query])

  if (!expr) return null

  return (
    <div className="py-2 flex items-baseline gap-3">
      <span className="font-mono text-sm" style={{ color: 'var(--muted)' }}>{expr} =</span>
      <span className="font-mono text-3xl font-bold" style={{
        color: result === '?' ? 'var(--red)' : 'var(--cyan)',
        textShadow: result !== '?' ? '0 0 16px rgba(0,200,255,.4)' : 'none',
      }}>
        {result}
      </span>
    </div>
  )
}
