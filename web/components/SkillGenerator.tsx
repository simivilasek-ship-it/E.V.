'use client'
import { useState } from 'react'
import { apiUrl } from '@/lib/api'

const EXAMPLE_PROMPTS: string[] = [
  'Plugin pro počasí v Brně',
  'Otevři moje oblíbené projekty ve VSCode',
  'Přečti RSS feed z hn.algolia.com',
  'Zobraz ceny kryptoměn z CoinGecko API',
  'Pošli notifikaci na desktop',
]

interface SkillResult {
  name: string
  skill_py: string
  manifest: Record<string, unknown>
  description?: string
  warning?: string
  triggers?: string[]
  error?: string
}

export default function SkillGenerator() {
  const [prompt,  setPrompt]  = useState<string>('')
  const [result,  setResult]  = useState<SkillResult | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error,   setError]   = useState<string | null>(null)
  const [saved,   setSaved]   = useState<boolean>(false)
  const [tab,     setTab]     = useState<'skill' | 'manifest'>('skill')

  async function generate(): Promise<void> {
    if (!prompt.trim()) return
    setLoading(true); setError(null); setResult(null); setSaved(false)
    try {
      const r = await fetch(apiUrl('/api/skill/generate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      })
      const d: SkillResult = await r.json()
      if (d.error) throw new Error(d.error)
      setResult(d)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    }
    setLoading(false)
  }

  async function save(): Promise<void> {
    if (!result) return
    try {
      const r = await fetch(apiUrl('/api/skill/save'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: result.name, skill_code: result.skill_py, manifest: result.manifest }),
      })
      const d: { error?: string } = await r.json()
      if (d.error) throw new Error(d.error)
      setSaved(true)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const S = {
    card: { background: 'var(--bg-hud)', border: '1px solid var(--border-hud)', borderRadius: 8, padding: '14px 16px', marginBottom: 12 },
    title: { color: 'var(--muted)', fontSize: 9, letterSpacing: '.15em', marginBottom: 8 },
    pre: {
      background: 'var(--bg)', border: '1px solid var(--border-hud)', borderRadius: 6,
      padding: '12px 14px', fontSize: 11, color: 'var(--text2)', overflowX: 'auto' as const,
      fontFamily: 'monospace', lineHeight: 1.6, whiteSpace: 'pre-wrap' as const, wordBreak: 'break-word' as const,
    },
    tab: (active: boolean): React.CSSProperties => ({
      padding: '4px 12px', fontSize: 11, cursor: 'pointer', borderRadius: '4px 4px 0 0',
      background: active ? 'var(--bg-hud)' : 'transparent',
      color: active ? 'var(--metric-cpu)' : 'var(--muted)',
      border: active ? '1px solid var(--border-hud)' : '1px solid transparent',
      borderBottom: active ? '1px solid var(--bg-hud)' : 'none',
    }),
  }

  return (
    <div style={{ fontFamily: 'IBM Plex Mono, monospace', color: 'var(--text)' }}>
      <div style={S.title}>AUTO-SKILL GENERATION — napiš co má plugin dělat, JARVIS napíše kód</div>

      {/* Prompt */}
      <div style={S.card}>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Napiš co má plugin dělat, např.: Plugin který zjistí aktuální cenu BTC a vrátí ji v CZK..."
          rows={3}
          style={{
            width: '100%', background: 'var(--bg)', border: '1px solid var(--border-hud)', borderRadius: 6,
            color: 'var(--text)', padding: '10px 12px', fontSize: 12, resize: 'vertical',
            fontFamily: 'monospace', outline: 'none',
          }}
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
          {EXAMPLE_PROMPTS.map(p => (
            <button key={p} onClick={() => setPrompt(p)} style={{
              background: 'var(--bg-hud)', border: '1px solid var(--border-hud)', borderRadius: 20,
              color: 'var(--muted)', padding: '3px 10px', fontSize: 10, cursor: 'pointer',
            }}>
              {p}
            </button>
          ))}
          <button
            onClick={generate}
            disabled={loading || !prompt.trim()}
            style={{
              marginLeft: 'auto', background: loading ? 'var(--border-hud)' : 'var(--metric-cpu)',
              border: 'none', borderRadius: 6, color: 'var(--bg)', padding: '6px 16px',
              fontSize: 12, fontWeight: 600, cursor: loading ? 'default' : 'pointer',
            }}>
            {loading ? '⟳ Generuji…' : '⚡ Generovat'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ ...S.card, border: '1px solid rgba(239,68,68,.27)', color: 'var(--red)', fontSize: 12 }}>
          ⚠ {error}
        </div>
      )}

      {result && (
        <div style={S.card}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
            <div style={{ color: result.warning ? 'var(--amber)' : 'var(--green)', fontSize: 12 }}>
              {result.warning ? `⚠ ${result.warning}` : `✓ Vygenerováno: `}
              <strong>{result.name}</strong>
            </div>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
              {saved && (
                <a href={apiUrl(`/api/skill/download/${result.name}`)} download
                  style={{
                  background: 'var(--border-hud)', border: 'none', borderRadius: 6,
                  color: 'var(--metric-cpu)', padding: '5px 12px', fontSize: 11,
                    fontWeight: 600, cursor: 'pointer', textDecoration: 'none',
                  }}>
                  📥 ZIP
                </a>
              )}
              <button onClick={save} disabled={saved} style={{
                background: saved ? 'rgba(16,185,129,.15)' : 'var(--green)',
                border: 'none', borderRadius: 6, color: 'var(--bg)', padding: '5px 14px',
                fontSize: 11, fontWeight: 600, cursor: saved ? 'default' : 'pointer',
              }}>
                {saved ? '✓ Uloženo' : '💾 Uložit plugin'}
              </button>
            </div>
          </div>

          {result.description && (
            <div style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 10 }}>{result.description}</div>
          )}

          {/* Tabs: skill.py | manifest.json */}
          <div style={{ display: 'flex', gap: 0, marginBottom: 0, borderBottom: '1px solid var(--border-hud)' }}>
            <button style={S.tab(tab === 'skill')}    onClick={() => setTab('skill')}>skill.py</button>
            <button style={S.tab(tab === 'manifest')} onClick={() => setTab('manifest')}>manifest.json</button>
          </div>

          <pre style={S.pre}>
            {tab === 'skill' ? result.skill_py : JSON.stringify(result.manifest, null, 2)}
          </pre>

          {(result.triggers?.length ?? 0) > 0 && (
            <div style={{ marginTop: 10, fontSize: 10, color: 'var(--muted)' }}>
              <span style={{ color: 'var(--muted)' }}>Triggery:</span>
              {result.triggers!.map(t => (
                <span key={t} style={{ background: 'var(--border-hud)', borderRadius: 3, padding: '1px 6px', marginLeft: 6, color: 'var(--text2)' }}>
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
