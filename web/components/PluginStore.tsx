'use client'
import { useEffect, useRef, useState } from 'react'
import { useJarvis } from '@/store/jarvis'

const REGISTRY: { name: string; desc: string; author: string }[] = [
  { name: 'hello-world', desc: 'Ukázkový plugin', author: 'JARVIS team' },
]

type Plugin = { name?: string; version?: string } | string

export default function PluginStore() {
  const plugins      = useJarvis(s => s.plugins) as Plugin[]
  const fetchPlugins = useJarvis(s => s.fetchPlugins) as () => void
  const sendCommand  = useJarvis(s => s.sendCommand) as (cmd: string) => void
  const [msg, setMsg] = useState<string>('')
  const ghInputRef    = useRef<HTMLInputElement>(null)

  useEffect(() => { fetchPlugins() }, [])

  const install = (name: string): void => {
    setMsg(`Instaluji ${name}...`)
    sendCommand(`nainstaluj plugin ${name}`)
    setTimeout(() => { setMsg(''); fetchPlugins() }, 2000)
  }

  const uninstall = (name: string): void => {
    setMsg(`Odinstalovuji ${name}...`)
    sendCommand(`odinstaluj plugin ${name}`)
    setTimeout(() => { setMsg(''); fetchPlugins() }, 2000)
  }

  const pluginName = (p: Plugin): string =>
    typeof p === 'string' ? p : (p.name ?? '')

  const pluginVersion = (p: Plugin): string =>
    typeof p === 'string' ? '1.0' : (p.version ?? '1.0')

  return (
    <div className="glass rounded-xl p-5 h-full" style={{ minHeight: 0 }}>
      <div className="text-xs tracking-widest mb-4" style={{ color: '#4a6080' }}>PLUGIN MARKETPLACE</div>

      {msg && (
        <div className="mb-3 text-xs px-3 py-2 rounded" style={{ background: 'rgba(0,212,255,0.1)', color: '#00d4ff' }}>
          {msg}
        </div>
      )}

      {/* Installed */}
      {plugins.length > 0 && (
        <div className="mb-4">
          <div className="text-xs mb-2" style={{ color: '#4a6080' }}>NAINSTALOVANÉ ({plugins.length})</div>
          <div className="grid grid-cols-2 gap-2">
            {plugins.map((p, i) => (
              <div key={i} className="flex items-center justify-between px-3 py-2 rounded"
                style={{ background: '#050a15', border: '1px solid #1a3050' }}>
                <div>
                  <div className="text-xs" style={{ color: '#e2f0ff' }}>{pluginName(p)}</div>
                  <div className="text-xs" style={{ color: '#4a6080' }}>v{pluginVersion(p)}</div>
                </div>
                <button onClick={() => uninstall(pluginName(p))}
                  className="text-xs px-2 py-0.5 rounded"
                  style={{ color: '#ff5252', border: '1px solid rgba(255,82,82,0.3)' }}>
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Registry */}
      <div>
        <div className="text-xs mb-2" style={{ color: '#4a6080' }}>DOSTUPNÉ</div>
        {REGISTRY.map((p, i) => (
          <div key={i} className="flex items-center justify-between px-3 py-3 mb-2 rounded"
            style={{ background: '#050a15', border: '1px solid #1a3050' }}>
            <div>
              <div className="text-sm" style={{ color: '#e2f0ff' }}>{p.name}</div>
              <div className="text-xs" style={{ color: '#4a6080' }}>{p.desc} · by {p.author}</div>
            </div>
            <button onClick={() => install(p.name)}
              className="text-xs px-3 py-1 rounded transition-all"
              style={{ background: 'rgba(0,153,187,0.2)', color: '#00d4ff', border: '1px solid rgba(0,212,255,0.3)' }}>
              Instalovat
            </button>
          </div>
        ))}
      </div>

      {/* GitHub install */}
      <div className="mt-3">
        <div className="text-xs mb-2" style={{ color: '#4a6080' }}>INSTALACE Z GITHUBU</div>
        <div className="flex gap-2">
          <input
            ref={ghInputRef}
            placeholder="user/repo nebo URL"
            className="flex-1 px-3 py-1.5 rounded text-xs outline-none"
            style={{ background: '#050a15', color: '#e2f0ff', border: '1px solid #1a3050' }}
          />
          <button
            onClick={() => {
              const v = ghInputRef.current?.value ?? ''
              if (v) {
                sendCommand(`nainstaluj z github ${v}`)
                if (ghInputRef.current) ghInputRef.current.value = ''
              }
            }}
            className="px-3 py-1.5 rounded text-xs"
            style={{ background: 'rgba(0,153,187,0.2)', color: '#00d4ff', border: '1px solid rgba(0,212,255,0.3)' }}>
            ↵
          </button>
        </div>
      </div>
    </div>
  )
}
