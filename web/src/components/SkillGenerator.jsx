import { useState } from 'react'

const API = import.meta.env.PROD
  ? `${window.location.protocol}//${window.location.host}`
  : 'http://localhost:8002'

const EXAMPLE_PROMPTS = [
  'Plugin pro počasí v Brně',
  'Otevři moje oblíbené projekty ve VSCode',
  'Přečti RSS feed z hn.algolia.com',
  'Zobraz ceny kryptoměn z CoinGecko API',
  'Pošli notifikaci na desktop',
]

export default function SkillGenerator() {
  const [prompt,   setPrompt]   = useState('')
  const [result,   setResult]   = useState(null)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)
  const [saved,    setSaved]    = useState(false)
  const [tab,      setTab]      = useState('skill')  // skill | manifest

  async function generate() {
    if (!prompt.trim()) return
    setLoading(true); setError(null); setResult(null); setSaved(false)
    try {
      const r = await fetch(`${API}/api/skill/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      })
      const d = await r.json()
      if (d.error) throw new Error(d.error)
      setResult(d)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  async function save() {
    if (!result) return
    try {
      const r = await fetch(`${API}/api/skill/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: result.name, skill_code: result.skill_py, manifest: result.manifest }),
      })
      const d = await r.json()
      if (d.error) throw new Error(d.error)
      setSaved(true)
    } catch (e) {
      setError(e.message)
    }
  }

  const S = {
    card: { background:'#0b1220', border:'1px solid #1a3050', borderRadius:8, padding:'14px 16px', marginBottom:12 },
    title: { color:'#475569', fontSize:9, letterSpacing:'.15em', marginBottom:8 },
    pre: {
      background:'#050a15', border:'1px solid #1a3050', borderRadius:6,
      padding:'12px 14px', fontSize:11, color:'#7ea8d4', overflowX:'auto',
      fontFamily:'monospace', lineHeight:1.6, whiteSpace:'pre-wrap', wordBreak:'break-word',
    },
    tab: (active) => ({
      padding:'4px 12px', fontSize:11, cursor:'pointer', borderRadius:'4px 4px 0 0',
      background: active ? '#0b1220' : 'transparent',
      color: active ? '#00d4ff' : '#475569',
      border: active ? '1px solid #1a3050' : '1px solid transparent',
      borderBottom: active ? '1px solid #0b1220' : 'none',
    }),
  }

  return (
    <div style={{ fontFamily: 'var(--font-mono,monospace)', color: '#e2f0ff' }}>
      <div style={S.title}>AUTO-SKILL GENERATION — napiš co má plugin dělat, JARVIS napíše kód</div>

      {/* Prompt */}
      <div style={S.card}>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Napiš co má plugin dělat, např.: Plugin který zjistí aktuální cenu BTC a vrátí ji v CZK..."
          rows={3}
          style={{
            width:'100%', background:'#050a15', border:'1px solid #1a3050', borderRadius:6,
            color:'#e2f0ff', padding:'10px 12px', fontSize:12, resize:'vertical',
            fontFamily:'monospace', outline:'none',
          }}
        />
        <div style={{ display:'flex', gap:8, marginTop:8, flexWrap:'wrap' }}>
          {EXAMPLE_PROMPTS.map(p => (
            <button key={p} onClick={() => setPrompt(p)} style={{
              background:'#0b1220', border:'1px solid #1a3050', borderRadius:20,
              color:'#475569', padding:'3px 10px', fontSize:10, cursor:'pointer',
            }}>
              {p}
            </button>
          ))}
          <button
            onClick={generate}
            disabled={loading || !prompt.trim()}
            style={{
              marginLeft:'auto', background: loading ? '#1a3050' : '#00d4ff',
              border:'none', borderRadius:6, color:'#000', padding:'6px 16px',
              fontSize:12, fontWeight:600, cursor: loading ? 'default' : 'pointer',
            }}>
            {loading ? '⟳ Generuji…' : '⚡ Generovat'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ ...S.card, border:'1px solid #ef444444', color:'#ef4444', fontSize:12 }}>
          ⚠ {error}
        </div>
      )}

      {result && (
        <div style={S.card}>
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:12 }}>
            <div style={{ color:'#10b981', fontSize:12 }}>✓ Vygenerováno: <strong>{result.name}</strong></div>
            <button onClick={save} disabled={saved} style={{
              marginLeft:'auto', background: saved ? '#064e3b' : '#10b981',
              border:'none', borderRadius:6, color:'#000', padding:'5px 14px',
              fontSize:11, fontWeight:600, cursor: saved ? 'default' : 'pointer',
            }}>
              {saved ? '✓ Uloženo do plugins/' : '💾 Uložit plugin'}
            </button>
          </div>

          {/* Popis */}
          {result.description && (
            <div style={{ fontSize:12, color:'#7ea8d4', marginBottom:10 }}>{result.description}</div>
          )}

          {/* Taby: skill.py | manifest.json */}
          <div style={{ display:'flex', gap:0, marginBottom:0, borderBottom:'1px solid #1a3050' }}>
            <button style={S.tab(tab==='skill')}    onClick={() => setTab('skill')}>skill.py</button>
            <button style={S.tab(tab==='manifest')} onClick={() => setTab('manifest')}>manifest.json</button>
          </div>

          <pre style={S.pre}>
            {tab === 'skill' ? result.skill_py : JSON.stringify(result.manifest, null, 2)}
          </pre>

          {result.triggers?.length > 0 && (
            <div style={{ marginTop:10, fontSize:10, color:'#475569' }}>
              <span style={{ color:'#2d3748' }}>Triggery:</span>
              {result.triggers.map(t => (
                <span key={t} style={{ background:'#1a3050', borderRadius:3, padding:'1px 6px', marginLeft:6, color:'#7ea8d4' }}>
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
