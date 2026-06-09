'use client'
import { useEffect, useState, useCallback } from 'react'
import { useJarvis } from '@/store/jarvis'
import { apiUrl } from '@/lib/api'
import AuditLogPanel from '@/components/AuditLogPanel'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Settings {
  model: string
  history_size: number
  tts_enabled: boolean
  tts_voice: string
  tts_rate: number
  tts_streaming: boolean
  stt_language: string
  stt_energy_threshold: number
  stt_timeout: number
  wake_word_enabled: boolean
  wake_word: string
  agent_max_steps: number
  agent_timeout: number
}

interface McpServer {
  name: string
  enabled: boolean
  command_found: boolean
  ready?: boolean
  requires_env?: string | null
  env_present?: boolean
  config_key?: string
  command?: string
}

interface HealthCheck {
  score: number
  checks_ok: number
  checks_total: number
  checks: Record<string, { ok: boolean; hint: string }>
  fixes: Array<{ key: string; hint: string }>
  mcp: {
    score: number
    enabled_total: number
    ready_total: number
  }
}

interface SliderRowProps {
  label: string
  value: number
  min: number
  max: number
  step: number
  onChange: (v: number) => void
  unit?: string
}

interface ToggleRowProps {
  label: string
  checked: boolean
  onChange: (v: boolean) => void
  desc?: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-5 flex flex-col gap-4">
      <h3
        className="font-hud text-[9px] tracking-widest uppercase"
        style={{ color: 'var(--muted)' }}
      >
        {title}
      </h3>
      {children}
    </div>
  )
}

function SliderRow({ label, value, min, max, step, onChange, unit = '' }: SliderRowProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between items-center">
        <span className="text-xs" style={{ color: 'var(--text)' }}>{label}</span>
        <span className="font-mono text-xs px-2 py-0.5 rounded"
          style={{ color: 'var(--cyan)', background: 'rgba(0,200,255,.08)', border: '1px solid var(--border)' }}>
          {value}{unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
        style={{
          background: `linear-gradient(to right, var(--cyan) 0%, var(--cyan) ${((value - min) / (max - min)) * 100}%, rgba(0,200,255,.12) ${((value - min) / (max - min)) * 100}%, rgba(0,200,255,.12) 100%)`,
          outline: 'none',
        }}
      />
    </div>
  )
}

function ToggleRow({ label, checked, onChange, desc }: ToggleRowProps) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex flex-col gap-0.5">
        <span className="text-xs" style={{ color: 'var(--text)' }}>{label}</span>
        {desc && <span className="text-[10px]" style={{ color: 'var(--muted)' }}>{desc}</span>}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className="relative flex-shrink-0 w-10 h-5 rounded-full transition-all duration-200 focus:outline-none"
        style={{
          background: checked ? 'var(--cyan)' : 'rgba(255,255,255,.08)',
          border: `1px solid ${checked ? 'var(--cyan)' : 'var(--border)'}`,
          boxShadow: checked ? '0 0 8px rgba(0,200,255,.35)' : 'none',
        }}
        aria-checked={checked}
        role="switch"
      >
        <span
          className="absolute top-0.5 w-4 h-4 rounded-full transition-all duration-200"
          style={{
            background: checked ? '#fff' : 'var(--muted)',
            left: checked ? 'calc(100% - 18px)' : '2px',
            boxShadow: '0 1px 3px rgba(0,0,0,.4)',
          }}
        />
      </button>
    </div>
  )
}

function SaveButton({ onClick, loading }: { onClick: () => void; loading: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="self-end px-4 py-1.5 rounded-lg text-xs font-mono transition-all duration-150"
      style={{
        background: loading ? 'rgba(0,200,255,.08)' : 'rgba(0,200,255,.15)',
        border: '1px solid var(--cyan)',
        color: 'var(--cyan)',
        opacity: loading ? 0.6 : 1,
        cursor: loading ? 'not-allowed' : 'pointer',
        boxShadow: loading ? 'none' : '0 0 8px rgba(0,200,255,.2)',
      }}
    >
      {loading ? 'Ukládám…' : 'Uložit'}
    </button>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function SettingsPanel() {
  const addToast = useJarvis(s => s.addToast)

  const [settings, setSettings] = useState<Settings>({
    model: '',
    history_size: 20,
    tts_enabled: false,
    tts_voice: '',
    tts_rate: 150,
    tts_streaming: false,
    stt_language: 'cs-CZ',
    stt_energy_threshold: 300,
    stt_timeout: 10,
    wake_word_enabled: false,
    wake_word: 'jarvis',
    agent_max_steps: 7,
    agent_timeout: 60,
  })

  const [models, setModels] = useState<string[]>([])
  const [voices, setVoices] = useState<string[]>([])
  const [mcpServers, setMcpServers] = useState<McpServer[]>([])
  const [health, setHealth] = useState<HealthCheck | null>(null)
  const [healthLoading, setHealthLoading] = useState(false)
  const [savingSection, setSavingSection] = useState<string | null>(null)
  const [testingVoice, setTestingVoice] = useState(false)
  const [loading, setLoading] = useState(true)
  const [generatingToken, setGeneratingToken] = useState(false)

  const patch = useCallback(<K extends keyof Settings>(key: K, value: Settings[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }, [])

  const refreshHealth = useCallback(async () => {
    setHealthLoading(true)
    try {
      const r = await fetch(apiUrl('/api/health/check'))
      if (r.ok) {
        const d = await r.json()
        setHealth(d)
      }
    } catch {
      // keep stale health data visible
    } finally {
      setHealthLoading(false)
    }
  }, [])

  // Load initial data
  useEffect(() => {
    const load = async () => {
      try {
        const [sRes, mRes, vRes, mcpRes, hRes] = await Promise.allSettled([
          fetch(apiUrl('/api/settings')),
          fetch(apiUrl('/api/models')),
          fetch(apiUrl('/api/tts/voices')),
          fetch(apiUrl('/api/mcp/status')),
          fetch(apiUrl('/api/health/check')),
        ])

        if (sRes.status === 'fulfilled' && sRes.value.ok) {
          const d = await sRes.value.json()
          setSettings(prev => ({ ...prev, ...d }))
        }

        if (mRes.status === 'fulfilled' && mRes.value.ok) {
          const d = await mRes.value.json()
          const list: string[] = Array.isArray(d) ? d : d.models ?? []
          setModels(list)
        }

        if (vRes.status === 'fulfilled' && vRes.value.ok) {
          const d = await vRes.value.json()
          const all: string[] = Array.isArray(d) ? d : d.voices ?? []
          const filtered = all.filter(
            v => v.toLowerCase().includes('cs') || v.toLowerCase().includes('en')
          )
          setVoices(filtered.length > 0 ? filtered : all)
        }

        if (mcpRes.status === 'fulfilled' && mcpRes.value.ok) {
          const d = await mcpRes.value.json()
          const servers: McpServer[] = Array.isArray(d) ? d : d.servers ?? []
          setMcpServers(servers)
        }
        if (hRes.status === 'fulfilled' && hRes.value.ok) {
          const d = await hRes.value.json()
          setHealth(d)
        }
      } catch (err) {
        console.error('Settings load error:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
    const healthInterval = setInterval(refreshHealth, 60_000)
    return () => clearInterval(healthInterval)
  }, [refreshHealth])

  const saveSection = useCallback(async (section: string, keys: (keyof Settings)[]) => {
    setSavingSection(section)
    try {
      const payload: Partial<Settings> = {}
      keys.forEach(k => { (payload as Record<string, unknown>)[k] = settings[k] })
      const r = await fetch(apiUrl('/api/config'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (r.ok) {
        addToast(`${section} uloženo`, 'success')
      } else {
        const err = await r.json().catch(() => ({}))
        addToast(err.detail ?? `Chyba při ukládání (${r.status})`, 'error')
      }
    } catch {
      addToast('Nelze se připojit k backendu', 'error')
    } finally {
      setSavingSection(null)
    }
  }, [settings, addToast])

  const testVoice = useCallback(async () => {
    setTestingVoice(true)
    try {
      const r = await fetch(apiUrl('/api/chat'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: 'kolik je hodin' }),
      })
      if (!r.ok) addToast('Test hlasu selhal', 'error')
    } catch {
      addToast('Test hlasu selhal — backend nedostupný', 'error')
    } finally {
      setTestingVoice(false)
    }
  }, [addToast])

  const toggleMcp = useCallback(async (server: McpServer) => {
    const next = !server.enabled
    setMcpServers(prev =>
      prev.map(s => s.name === server.name ? { ...s, enabled: next } : s)
    )
    try {
      const r = await fetch(apiUrl('/api/mcp/toggle'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ server: server.name, enabled: next }),
      })
      if (r.ok) {
        addToast(`MCP ${server.name} ${next ? 'zapnut' : 'vypnut'}`, 'success')
      } else {
        setMcpServers(prev =>
          prev.map(s => s.name === server.name ? { ...s, enabled: server.enabled } : s)
        )
        addToast(`Nelze přepnout MCP server`, 'error')
      }
    } catch {
      setMcpServers(prev =>
        prev.map(s => s.name === server.name ? { ...s, enabled: server.enabled } : s)
      )
      addToast('Backend nedostupný', 'error')
    }
  }, [addToast])

  const STT_LANGUAGES = [
    { value: 'cs-CZ', label: 'Čeština (cs-CZ)' },
    { value: 'en-US', label: 'English US (en-US)' },
    { value: 'en-GB', label: 'English GB (en-GB)' },
    { value: 'de-DE', label: 'Deutsch (de-DE)' },
    { value: 'fr-FR', label: 'Français (fr-FR)' },
    { value: 'es-ES', label: 'Español (es-ES)' },
    { value: 'pl-PL', label: 'Polski (pl-PL)' },
  ]

  const selectStyle: React.CSSProperties = {
    background: 'rgba(0,200,255,.04)',
    border: '1px solid var(--border)',
    borderRadius: 8,
    color: 'var(--text)',
    fontSize: 12,
    padding: '6px 10px',
    width: '100%',
    outline: 'none',
    cursor: 'pointer',
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center" style={{ color: 'var(--muted)' }}>
        <span className="font-mono text-xs animate-pulse">Načítám nastavení…</span>
      </div>
    )
  }

  return (
    <div
      className="flex-1 overflow-y-auto flex flex-col gap-4 p-4"
      style={{ scrollbarWidth: 'thin' }}
    >
      {/* ── Sekce 1: LLM Model ─────────────────────────────── */}
      <Section title="LLM Model">
        <div className="flex flex-col gap-1.5">
          <span className="text-xs" style={{ color: 'var(--text)' }}>Model</span>
          <select
            value={settings.model}
            onChange={e => patch('model', e.target.value)}
            style={selectStyle}
          >
            {models.length === 0 && (
              <option value={settings.model}>{settings.model || '— žádné modely —'}</option>
            )}
            {models.map(m => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          {settings.model && models.includes(settings.model) && (
            <span className="text-[10px]" style={{ color: 'var(--teal)' }}>
              ● Aktivní
            </span>
          )}
        </div>

        <SliderRow
          label="Velikost historie"
          value={settings.history_size}
          min={5}
          max={50}
          step={1}
          onChange={v => patch('history_size', v)}
          unit=" zpráv"
        />

        <SaveButton
          onClick={() => saveSection('LLM Model', ['model', 'history_size'])}
          loading={savingSection === 'LLM Model'}
        />
      </Section>

      {/* ── Sekce 2: TTS ───────────────────────────────────── */}
      <Section title="TTS — Hlas">
        <ToggleRow
          label="TTS zapnuto"
          checked={settings.tts_enabled}
          onChange={v => patch('tts_enabled', v)}
          desc="Text-to-speech syntéza hlasu"
        />

        <div className="flex flex-col gap-1.5">
          <span className="text-xs" style={{ color: 'var(--text)' }}>Hlas</span>
          <select
            value={settings.tts_voice}
            onChange={e => patch('tts_voice', e.target.value)}
            style={selectStyle}
            disabled={!settings.tts_enabled}
          >
            {voices.length === 0 && (
              <option value={settings.tts_voice}>{settings.tts_voice || '— žádné hlasy —'}</option>
            )}
            {voices.map(v => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </div>

        <SliderRow
          label="Rychlost řeči"
          value={settings.tts_rate}
          min={50}
          max={400}
          step={10}
          onChange={v => patch('tts_rate', v)}
          unit=" wpm"
        />

        <ToggleRow
          label="Streaming"
          checked={settings.tts_streaming}
          onChange={v => patch('tts_streaming', v)}
          desc="Streamovat audio průběžně"
        />

        <div className="flex gap-2 justify-end">
          <button
            onClick={testVoice}
            disabled={testingVoice}
            className="px-4 py-1.5 rounded-lg text-xs font-mono transition-all duration-150"
            style={{
              background: 'rgba(78,205,196,.1)',
              border: '1px solid var(--teal)',
              color: 'var(--teal)',
              opacity: testingVoice ? 0.6 : 1,
              cursor: testingVoice ? 'not-allowed' : 'pointer',
            }}
          >
            {testingVoice ? 'Testuji…' : 'Test hlasu'}
          </button>
          <SaveButton
            onClick={() => saveSection('TTS', ['tts_enabled', 'tts_voice', 'tts_rate', 'tts_streaming'])}
            loading={savingSection === 'TTS'}
          />
        </div>
      </Section>

      {/* ── Sekce 3: STT ───────────────────────────────────── */}
      <Section title="STT — Mikrofon">
        <div className="flex flex-col gap-1.5">
          <span className="text-xs" style={{ color: 'var(--text)' }}>Jazyk rozpoznávání</span>
          <select
            value={settings.stt_language}
            onChange={e => patch('stt_language', e.target.value)}
            style={selectStyle}
          >
            {STT_LANGUAGES.map(l => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>
        </div>

        <SliderRow
          label="Energy threshold"
          value={settings.stt_energy_threshold}
          min={100}
          max={2000}
          step={50}
          onChange={v => patch('stt_energy_threshold', v)}
        />

        <SliderRow
          label="Timeout"
          value={settings.stt_timeout}
          min={3}
          max={30}
          step={1}
          onChange={v => patch('stt_timeout', v)}
          unit="s"
        />

        <ToggleRow
          label="Wake word"
          checked={settings.wake_word_enabled}
          onChange={v => patch('wake_word_enabled', v)}
          desc="Čekat na probuzovací slovo"
        />

        {settings.wake_word_enabled && (
          <div className="flex flex-col gap-1.5">
            <span className="text-xs" style={{ color: 'var(--text)' }}>Wake word</span>
            <input
              type="text"
              value={settings.wake_word}
              onChange={e => patch('wake_word', e.target.value)}
              placeholder="jarvis"
              style={{
                ...selectStyle,
                padding: '7px 10px',
              }}
            />
          </div>
        )}

        <SaveButton
          onClick={() =>
            saveSection('STT', [
              'stt_language',
              'stt_energy_threshold',
              'stt_timeout',
              'wake_word_enabled',
              'wake_word',
            ])
          }
          loading={savingSection === 'STT'}
        />
      </Section>

      {/* ── Sekce 4: Agenti ────────────────────────────────── */}
      <Section title="Agenti">
        <SliderRow
          label="Max kroků"
          value={settings.agent_max_steps}
          min={3}
          max={15}
          step={1}
          onChange={v => patch('agent_max_steps', v)}
          unit=" kroků"
        />

        <SliderRow
          label="Timeout"
          value={settings.agent_timeout}
          min={30}
          max={300}
          step={10}
          onChange={v => patch('agent_timeout', v)}
          unit="s"
        />

        <SaveButton
          onClick={() => saveSection('Agenti', ['agent_max_steps', 'agent_timeout'])}
          loading={savingSection === 'Agenti'}
        />
      </Section>

      {/* ── Sekce 5: MCP Servery ───────────────────────────── */}
      <Section title="MCP Servery">
        {mcpServers.length === 0 ? (
          <span className="text-xs" style={{ color: 'var(--muted)' }}>
            Žádné MCP servery nenalezeny
          </span>
        ) : (
          <div className="flex flex-col gap-3">
            {mcpServers.map(server => (
              <div
                key={server.name}
                className="flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl"
                style={{
                  background: 'rgba(255,255,255,.025)',
                  border: '1px solid var(--border2)',
                }}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <span
                    title={server.ready ? 'Server je připraven' : server.command_found ? 'Chybí env / disabled' : 'Příkaz není v PATH'}
                    style={{
                      width: 7,
                      height: 7,
                      borderRadius: '50%',
                      flexShrink: 0,
                      background: server.ready ? 'var(--green)' : server.command_found ? 'var(--yellow)' : 'var(--red)',
                      boxShadow: server.ready
                        ? '0 0 6px rgba(34,211,165,.6)'
                        : server.command_found
                          ? '0 0 6px rgba(234,179,8,.5)'
                          : '0 0 6px rgba(244,63,94,.5)',
                    }}
                  />
                  <div className="flex flex-col min-w-0">
                    <span
                      className="text-xs font-mono truncate"
                      style={{ color: 'var(--text)' }}
                    >
                      {server.name}
                    </span>
                    {server.command && (
                      <span
                        className="text-[10px] font-mono truncate"
                        style={{ color: 'var(--muted)' }}
                      >
                        {server.command}
                        {server.requires_env ? ` · ${server.requires_env}` : ''}
                      </span>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => toggleMcp(server)}
                  className="relative flex-shrink-0 w-10 h-5 rounded-full transition-all duration-200 focus:outline-none"
                  style={{
                    background: server.enabled ? 'var(--cyan)' : 'rgba(255,255,255,.08)',
                    border: `1px solid ${server.enabled ? 'var(--cyan)' : 'var(--border)'}`,
                    boxShadow: server.enabled ? '0 0 8px rgba(0,200,255,.35)' : 'none',
                  }}
                  aria-checked={server.enabled}
                  role="switch"
                >
                  <span
                    className="absolute top-0.5 w-4 h-4 rounded-full transition-all duration-200"
                    style={{
                      background: server.enabled ? '#fff' : 'var(--muted)',
                      left: server.enabled ? 'calc(100% - 18px)' : '2px',
                      boxShadow: '0 1px 3px rgba(0,0,0,.4)',
                    }}
                  />
                </button>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Health Check (Linux)">
        <div className="flex items-center justify-between">
          <span className="text-xs" style={{ color: 'var(--muted)' }}>
            Automaticky obnovuje každých 60s
          </span>
          <button
            onClick={refreshHealth}
            disabled={healthLoading}
            className="text-xs px-2 py-1 rounded hover:bg-white/5 transition-colors"
            style={{ color: 'var(--cyan)', border: '1px solid var(--border)' }}
          >
            {healthLoading ? '⏳ kontroluji…' : '↻ refresh'}
          </button>
        </div>

        {healthLoading && !health && (
          <div className="flex items-center justify-center p-6">
            <div className="animate-spin h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full" />
          </div>
        )}

        {health ? (
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs" style={{ color: 'var(--text)' }}>
                Ready Score
              </span>
              <span className="font-mono text-xs px-2 py-0.5 rounded"
                style={{ color: 'var(--cyan)', background: 'rgba(0,200,255,.08)', border: '1px solid var(--border)' }}>
                {health.score}%
              </span>
            </div>
            <div className="text-[11px]" style={{ color: 'var(--muted)' }}>
              Checks: {health.checks_ok}/{health.checks_total} · MCP: {health.mcp.ready_total}/{health.mcp.enabled_total} ready
            </div>
            {health.checks['api_auth'] && !health.checks['api_auth'].ok && (
              <div
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-[11px] font-mono"
                style={{
                  background: 'rgba(244,63,94,.1)',
                  border: '1px solid rgba(244,63,94,.4)',
                  color: '#f43f5e',
                }}
              >
                <span>⚠</span>
                <span>API bez autentizace — zapni <strong>api_auth_required</strong> v config.json</span>
              </div>
            )}
            {health.mcp.ready_total < health.mcp.enabled_total && (
              <div className="text-[10px] px-2 py-1.5 rounded" style={{ background: 'rgba(251,191,36,.06)', border: '1px solid rgba(251,191,36,.2)', color: 'var(--amber)' }}>
                ⚠ {health.mcp.enabled_total - health.mcp.ready_total} MCP server(y) nejsou připraveny — zkontroluj chybějící balíčky v sekci MCP Servery
              </div>
            )}
            <div className="flex flex-col gap-2">
              {Object.entries(health.checks).map(([key, value]) => (
                <div key={key} className="flex items-start gap-2 text-[11px]">
                  <span style={{ color: value.ok ? 'var(--green)' : 'var(--red)' }}>{value.ok ? '✓' : '✗'}</span>
                  <span style={{ color: 'var(--text)' }}>{key}</span>
                  {!value.ok && (
                    <span className="text-[10px]" style={{ color: 'var(--muted)' }}>— {value.hint}</span>
                  )}
                </div>
              ))}
            </div>
            {health.fixes.length > 0 && (
              <div className="text-[11px] rounded-lg p-2" style={{ background: 'rgba(255,255,255,.03)', border: '1px solid var(--border2)' }}>
                <div className="font-mono mb-1" style={{ color: 'var(--text)' }}>Fix hints</div>
                {health.fixes.map((f, i) => (
                  <div key={`${f.key}-${i}`} style={{ color: 'var(--muted)' }}>- {f.hint}</div>
                ))}
              </div>
            )}
          </div>
        ) : (
          !healthLoading && <span className="text-xs" style={{ color: 'var(--muted)' }}>Health check nedostupný — backend offline</span>
        )}
      </Section>

      <Section title="API Token">
        <div className="flex flex-col gap-2">
          <span className="text-xs" style={{ color: 'var(--muted)' }}>
            Vygeneruj bezpečný API token pro JARVIS_API_TOKEN v .env souboru
          </span>
          <button
            onClick={async () => {
              setGeneratingToken(true)
              try {
                const res = await fetch(apiUrl('/api/settings/generate-token'), { method: 'POST' })
                if (!res.ok) throw new Error(`HTTP ${res.status}`)
                const { token } = await res.json()
                navigator.clipboard?.writeText(token)
                addToast(`Token vygenerován a zkopírován: ${token.slice(0, 8)}…`, 'success', 4000)
              } catch {
                addToast('Backend offline — spusť: python scripts/generate_token.py --write', 'error', 5000)
              } finally {
                setGeneratingToken(false)
              }
            }}
            disabled={generatingToken}
            className="self-start px-3 py-1.5 text-sm rounded-lg font-mono transition-all duration-150"
            style={{
              background: generatingToken ? 'rgba(59,130,246,.06)' : 'rgba(59,130,246,.12)',
              border: '1px solid var(--blue)',
              color: 'var(--blue)',
              opacity: generatingToken ? 0.6 : 1,
              cursor: generatingToken ? 'not-allowed' : 'pointer',
            }}
          >
            {generatingToken ? 'Generuji…' : 'Generovat token'}
          </button>
        </div>
      </Section>

      <AuditLogPanel />
    </div>
  )
}
