'use client'

import { useEffect, useState, useCallback } from 'react'

// ── Typy ─────────────────────────────────────────────────────────────────────

interface Plugin {
  id: string
  name: string
  description: string
  author: string
  version: string
  rating: number
  reviews: number
  downloads: number
  tags: string[]
  builtin: boolean
  installed: boolean
  has_update: boolean
  new_version?: string
}

interface Review {
  rating: number
  comment: string
  ts: number
}

type FilterTag = 'all' | 'installed' | 'builtin' | 'updates'

// ── Helpers ───────────────────────────────────────────────────────────────────

function Stars({ rating, size = 12 }: { rating: number; size?: number }) {
  const full  = Math.floor(rating)
  const half  = rating % 1 >= 0.5
  const empty = 5 - full - (half ? 1 : 0)
  return (
    <span style={{ fontSize: size, letterSpacing: 1 }}>
      {'★'.repeat(full)}
      {half ? '½' : ''}
      {'☆'.repeat(empty)}
    </span>
  )
}

function TagBadge({ tag }: { tag: string }) {
  const colors: Record<string, string> = {
    builtin: '#1e3a5f', mcp: '#1e4a3f', math: '#3a2a1e',
    search: '#2a1e4a', system: '#2a2a2a', demo: '#3a3a1e',
    productivity: '#1e3a2a', files: '#1e2a3a', conversation: '#2a1e3a',
  }
  return (
    <span style={{
      fontSize: 9, padding: '1px 6px', borderRadius: 3,
      background: colors[tag] || 'var(--bg-elevated)',
      color: 'var(--text2)', letterSpacing: '0.1em',
      fontFamily: "'Courier New', monospace",
    }}>
      {tag}
    </span>
  )
}

// ── Hlavní komponenta ─────────────────────────────────────────────────────────

export default function PluginMarketplace() {
  const [plugins, setPlugins]       = useState<Plugin[]>([])
  const [loading, setLoading]       = useState(true)
  const [filter, setFilter]         = useState<FilterTag>('all')
  const [search, setSearch]         = useState('')
  const [selected, setSelected]     = useState<Plugin | null>(null)
  const [reviews, setReviews]       = useState<Review[]>([])
  const [reviewAvg, setReviewAvg]   = useState(0)
  const [ratingInput, setRating]    = useState(5)
  const [comment, setComment]       = useState('')
  const [actionMsg, setActionMsg]   = useState('')
  const [actionBusy, setBusy]       = useState<string | null>(null)

  const fetchCatalog = useCallback(async () => {
    setLoading(true)
    try {
      const r = await fetch('/api/marketplace')
      const d = await r.json()
      setPlugins(d.plugins || [])
    } catch {
      setPlugins([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchCatalog() }, [fetchCatalog])

  const fetchReviews = async (id: string) => {
    try {
      const r = await fetch(`/api/marketplace/reviews/${id}`)
      const d = await r.json()
      setReviews(d.reviews || [])
      setReviewAvg(d.avg || 0)
    } catch {
      setReviews([])
    }
  }

  const selectPlugin = (p: Plugin) => {
    setSelected(p)
    fetchReviews(p.id)
    setActionMsg('')
  }

  const action = async (type: 'install' | 'uninstall' | 'update', id: string) => {
    setBusy(id + type)
    setActionMsg('')
    try {
      const method = type === 'uninstall' ? 'DELETE' : 'POST'
      const url = type === 'update'
        ? `/api/marketplace/update/${id}`
        : type === 'install'
          ? `/api/marketplace/install/${id}`
          : `/api/marketplace/uninstall/${id}`
      const r = await fetch(url, { method })
      const d = await r.json()
      setActionMsg(d.message || (d.ok ? 'Hotovo.' : 'Chyba.'))
      await fetchCatalog()
      if (selected?.id === id) {
        const updated = plugins.find(p => p.id === id)
        if (updated) setSelected({ ...updated, installed: type !== 'uninstall' })
      }
    } catch (e) {
      setActionMsg(`Chyba: ${e}`)
    } finally {
      setBusy(null)
    }
  }

  const submitReview = async () => {
    if (!selected) return
    setBusy('review')
    try {
      await fetch(`/api/marketplace/review/${selected.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating: ratingInput, comment }),
      })
      setComment('')
      setRating(5)
      await fetchReviews(selected.id)
      await fetchCatalog()
    } catch { /* ignore */ }
    finally { setBusy(null) }
  }

  // Filtrování + vyhledávání
  const visible = plugins.filter(p => {
    if (filter === 'installed' && !p.installed) return false
    if (filter === 'builtin'   && !p.builtin)   return false
    if (filter === 'updates'   && !p.has_update) return false
    if (search) {
      const q = search.toLowerCase()
      return p.name.includes(q) || p.description.toLowerCase().includes(q) ||
             p.tags.some(t => t.includes(q))
    }
    return true
  })

  const updates = plugins.filter(p => p.has_update).length

  // ── Styly ────────────────────────────────────────────────────────────────

  const mono: React.CSSProperties = { fontFamily: "'Courier New', monospace" }

  const panel: React.CSSProperties = {
    background: 'var(--bg-hud)', border: '1px solid var(--border-hud)',
    borderRadius: 8, ...mono,
  }

  const btn = (color: string, disabled = false): React.CSSProperties => ({
    padding: '5px 12px', fontSize: 10, borderRadius: 4, cursor: disabled ? 'not-allowed' : 'pointer',
    border: `1px solid ${color}44`, background: `${color}18`, color: disabled ? '#4a6a8a' : color,
    letterSpacing: '0.1em', opacity: disabled ? 0.6 : 1, ...mono,
  })

  return (
    <div style={{ display: 'flex', gap: 16, height: '100%', padding: 16, ...mono }}>

      {/* ── Levý panel: katalog ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>

        {/* Toolbar */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Hledat plugin..."
            style={{
              flex: 1, minWidth: 140, padding: '5px 10px', fontSize: 11,
              background: 'var(--bg-elevated)', border: '1px solid var(--border-hud)', borderRadius: 4,
              color: 'var(--text2)', ...mono, outline: 'none',
            }}
          />
          {(['all', 'installed', 'builtin', 'updates'] as FilterTag[]).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              style={{
                ...btn(filter === f ? 'var(--metric-cpu)' : 'var(--muted)'),
                background: filter === f ? 'rgba(0,212,255,.13)' : 'transparent',
              }}>
              {f === 'updates' && updates > 0 ? `updates (${updates})` : f}
            </button>
          ))}
          <button onClick={fetchCatalog} style={btn('var(--text2)')}>↻</button>
        </div>

        {/* Seznam pluginů */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {loading && (
            <div style={{ color: '#4a6a8a', fontSize: 11, padding: 20, textAlign: 'center' }}>
              Načítám katalog…
            </div>
          )}
          {!loading && visible.length === 0 && (
            <div style={{ color: '#4a6a8a', fontSize: 11, padding: 20, textAlign: 'center' }}>
              Žádné pluginy nenalezeny.
            </div>
          )}
          {visible.map(p => (
            <div key={p.id}
              onClick={() => selectPlugin(p)}
              style={{
                ...panel,
                padding: '10px 14px',
                cursor: 'pointer',
                borderColor: selected?.id === p.id ? 'rgba(0,212,255,.27)' : 'var(--border-hud)',
                background: selected?.id === p.id ? 'rgba(0,212,255,.03)' : 'var(--bg-hud)',
                transition: 'all 0.2s',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span style={{ fontSize: 12, color: 'var(--text)', fontWeight: 600 }}>{p.name}</span>
                <span style={{ fontSize: 9, color: 'var(--muted)' }}>v{p.version}</span>
                {p.installed && <span style={{ fontSize: 9, color: '#00e5a0' }}>✓ nainstalován</span>}
                {p.has_update && (
                  <span style={{ fontSize: 9, color: '#ffb300' }}>⬆ {p.new_version}</span>
                )}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text2)', marginBottom: 6 }}>{p.description}</div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                <span style={{ color: '#f59e0b', fontSize: 11 }}>
                  <Stars rating={p.rating} />
                </span>
                <span style={{ fontSize: 9, color: 'var(--muted)' }}>{p.rating} ({p.reviews})</span>
                <span style={{ fontSize: 9, color: 'var(--muted)' }}>↓ {p.downloads}</span>
                {p.tags.slice(0, 3).map(t => <TagBadge key={t} tag={t} />)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Pravý panel: detail pluginu ── */}
      {selected ? (
        <div style={{ width: 300, display: 'flex', flexDirection: 'column', gap: 10 }}>

          {/* Header */}
          <div style={{ ...panel, padding: 16 }}>
            <div style={{ fontSize: 14, color: 'var(--text)', marginBottom: 4 }}>{selected.name}</div>
            <div style={{ fontSize: 10, color: 'var(--muted)', marginBottom: 8 }}>
              by {selected.author} · v{selected.version}
            </div>
            <div style={{ fontSize: 10, color: 'var(--text2)', marginBottom: 12, lineHeight: 1.6 }}>
              {selected.description}
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
              {selected.tags.map(t => <TagBadge key={t} tag={t} />)}
            </div>

            {/* Akce */}
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {!selected.installed && (
                <button onClick={() => action('install', selected.id)}
                  disabled={actionBusy === selected.id + 'install'}
                  style={btn('#00e5a0', actionBusy === selected.id + 'install')}>
                  {actionBusy === selected.id + 'install' ? '…' : '↓ Instalovat'}
                </button>
              )}
              {selected.installed && (
                <button onClick={() => action('uninstall', selected.id)}
                  disabled={!!actionBusy}
                  style={btn('#ef4444', !!actionBusy)}>
                  Odinstalovat
                </button>
              )}
              {selected.has_update && (
                <button onClick={() => action('update', selected.id)}
                  disabled={!!actionBusy}
                  style={btn('#ffb300', !!actionBusy)}>
                  ⬆ Aktualizovat na {selected.new_version}
                </button>
              )}
            </div>

            {actionMsg && (
              <div style={{ marginTop: 8, fontSize: 10, color: '#00e5a0', lineHeight: 1.5 }}>
                {actionMsg}
              </div>
            )}
          </div>

          {/* Hodnocení */}
          <div style={{ ...panel, padding: 14 }}>
            <div style={{ fontSize: 9, letterSpacing: '0.2em', color: 'var(--muted)', marginBottom: 10 }}>
              HODNOCENÍ · <span style={{ color: '#f59e0b' }}><Stars rating={reviewAvg} /></span> {reviewAvg} ({reviews.length})
            </div>

            {/* Přidat hodnocení */}
            <div style={{ marginBottom: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', gap: 4 }}>
                {[1,2,3,4,5].map(n => (
                  <button key={n} onClick={() => setRating(n)}
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer',
                      fontSize: 16, color: n <= ratingInput ? 'var(--amber)' : 'var(--border-hud)',
                    }}>★</button>
                ))}
              </div>
              <input
                value={comment}
                onChange={e => setComment(e.target.value)}
                placeholder="Váš komentář (nepovinné)"
                style={{
                  padding: '4px 8px', fontSize: 10, background: 'var(--bg-elevated)',
                  border: '1px solid var(--border-hud)', borderRadius: 4, color: 'var(--text2)',
                  ...mono, outline: 'none',
                }}
              />
              <button onClick={submitReview} disabled={actionBusy === 'review'}
                style={btn('#6366f1', actionBusy === 'review')}>
                Odeslat hodnocení
              </button>
            </div>

            {/* Seznam hodnocení */}
            <div style={{ maxHeight: 180, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
              {reviews.length === 0 && (
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Zatím žádná hodnocení.</div>
              )}
              {reviews.slice().reverse().map((r, i) => (
                <div key={i} style={{
                  padding: '6px 8px', background: 'var(--bg-elevated)',
                  borderRadius: 4, border: '1px solid var(--border-hud)',
                }}>
                  <div style={{ color: '#f59e0b', fontSize: 11, marginBottom: 2 }}>
                    <Stars rating={r.rating} size={10} /> {r.rating}★
                  </div>
                  {r.comment && (
                    <div style={{ fontSize: 10, color: 'var(--text2)', lineHeight: 1.5 }}>{r.comment}</div>
                  )}
                  <div style={{ fontSize: 9, color: 'var(--muted)', marginTop: 2 }}>
                    {new Date(r.ts * 1000).toLocaleDateString('cs-CZ')}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div style={{
          width: 300, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#2a4060', fontSize: 11, ...mono, textAlign: 'center',
        }}>
          Vyber plugin pro detail,<br />instalaci nebo hodnocení.
        </div>
      )}
    </div>
  )
}
