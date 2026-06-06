'use client'

import { useState } from 'react'
import { apiUrl } from '@/lib/api'

interface Preview {
  id: string
  target: string
  x: number
  y: number
  method: string
  matched_text: string
  screenshot_b64: string
  screen_w: number
  screen_h: number
}

export default function VisionSandboxPanel() {
  const [target, setTarget] = useState('')
  const [preview, setPreview] = useState<Preview | null>(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')

  async function runPreview() {
    if (!target.trim()) return
    setLoading(true)
    setStatus('')
    setPreview(null)
    try {
      const r = await fetch(apiUrl('/api/vision/sandbox/preview'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: target.trim() }),
      })
      const data = await r.json()
      if (data.found && data.id) {
        setPreview(data as Preview)
        setStatus('Náhled připraven — schval nebo zamítni klik')
      } else {
        setStatus(data.error || 'Cíl nenalezen')
      }
    } catch {
      setStatus('Chyba připojení k API')
    } finally {
      setLoading(false)
    }
  }

  async function decide(approved: boolean) {
    if (!preview) return
    setLoading(true)
    try {
      const r = await fetch(apiUrl('/api/vision/sandbox/execute'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preview_id: preview.id, approved }),
      })
      const data = await r.json()
      if (approved && data.executed) {
        setStatus(`Provedeno ✓ klik @ (${preview.x}, ${preview.y})`)
      } else if (!approved) {
        setStatus('Zamítnuto — klik neproveden')
      } else {
        setStatus(data.error || 'Akce selhala')
      }
      setPreview(null)
    } catch {
      setStatus('Chyba při execute')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card p-5 flex flex-col gap-4">
      <div>
        <h3 className="font-hud text-[9px] tracking-widest uppercase mb-1" style={{ color: 'var(--muted)' }}>
          Vision Sandbox (dry-run)
        </h3>
        <p className="text-[11px]" style={{ color: 'var(--muted)' }}>
          Agent ukáže cíl kliknutí na screenshotu — nic se neprovede bez tvého schválení.
        </p>
      </div>

      <div className="flex gap-2 flex-wrap">
        <input
          value={target}
          onChange={e => setTarget(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && runPreview()}
          placeholder='např. "tlačítko Přihlásit"'
          className="flex-1 min-w-[200px] text-sm px-3 py-2 rounded-lg font-mono"
          style={{ background: 'rgba(255,255,255,.04)', border: '1px solid var(--border)', color: 'var(--text)' }}
        />
        <button
          type="button"
          onClick={runPreview}
          disabled={loading}
          className="px-4 py-2 rounded-lg text-xs font-hud tracking-wider"
          style={{ background: 'rgba(0,200,255,.12)', border: '1px solid var(--cyan)', color: 'var(--cyan)' }}
        >
          {loading ? '…' : 'NÁHLED'}
        </button>
      </div>

      {status && (
        <p className="text-xs font-mono" style={{ color: status.includes('✓') ? 'var(--green)' : 'var(--muted)' }}>
          {status}
        </p>
      )}

      {preview && (
        <div className="flex flex-col gap-3">
          <div className="text-xs font-mono flex flex-wrap gap-3" style={{ color: 'var(--text)' }}>
            <span>Cíl: <strong>{preview.target}</strong></span>
            <span>@ ({preview.x}, {preview.y})</span>
            <span style={{ color: 'var(--cyan)' }}>{preview.method}</span>
            {preview.matched_text && <span>„{preview.matched_text}"</span>}
          </div>
          {preview.screenshot_b64 && (
            <div className="rounded-lg overflow-hidden border" style={{ borderColor: 'var(--border)', maxHeight: 360 }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                alt="Sandbox preview"
                src={`data:image/jpeg;base64,${preview.screenshot_b64}`}
                className="w-full h-auto object-contain"
              />
            </div>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => decide(true)}
              disabled={loading}
              className="px-4 py-2 rounded-lg text-xs font-hud"
              style={{ background: 'rgba(34,211,165,.15)', border: '1px solid var(--green)', color: 'var(--green)' }}
            >
              Povolit klik
            </button>
            <button
              type="button"
              onClick={() => decide(false)}
              disabled={loading}
              className="px-4 py-2 rounded-lg text-xs font-hud"
              style={{ background: 'rgba(244,63,94,.1)', border: '1px solid var(--red)', color: 'var(--red)' }}
            >
              Zamítnout
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
