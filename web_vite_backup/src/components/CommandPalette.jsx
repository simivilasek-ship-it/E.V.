import { useState, useEffect, useRef, useCallback } from 'react'
import { useJarvis } from '../store/jarvis'

const COMMANDS = [
  // Navigace
  { id: 'nav-chat',    label: 'Přejít na Chat',      icon: '💬', action: 'nav', value: 'CHAT' },
  { id: 'nav-plugins', label: 'Přejít na Plugins',   icon: '🔌', action: 'nav', value: 'PLUGINY' },
  { id: 'nav-system',  label: 'Přejít na System',    icon: '📊', action: 'nav', value: 'SYSTÉM' },
  { id: 'nav-agent',   label: 'Přejít na Agent',     icon: '🤖', action: 'nav', value: 'AGENT' },
  // Modely
  { id: 'model-qwen',  label: 'Model: qwen2.5:3b',  icon: '🧠', action: 'model', value: 'qwen2.5:3b' },
  { id: 'model-llama', label: 'Model: llama3.1:8b', icon: '🦙', action: 'model', value: 'llama3.1:8b' },
  { id: 'model-llava', label: 'Model: llava:7b',    icon: '👁',  action: 'model', value: 'llava:7b' },
  // Akce
  { id: 'clear-chat',  label: 'Vymazat chat',        icon: '🗑',  action: 'clear' },
  { id: 'screenshot',  label: 'Udělat screenshot',   icon: '📸', action: 'cmd', value: 'screenshot' },
  { id: 'hardware',    label: 'Info o hardwaru',     icon: '💻', action: 'cmd', value: 'jaky mam hardware' },
  { id: 'disk',        label: 'Místo na disku',      icon: '💾', action: 'cmd', value: 'kolik mam mista na disku' },
  { id: 'disk-home',   label: 'Obsah domovské složky', icon: '📁', action: 'cmd', value: 'obsah domovske slozky' },
  { id: 'weather',     label: 'Počasí Praha',        icon: '🌤', action: 'cmd', value: 'počasí Praha' },
  { id: 'time',        label: 'Kolik je hodin',      icon: '🕐', action: 'cmd', value: 'kolik je hodin' },
  // Pluginy
  { id: 'marketplace', label: 'Marketplace seznam', icon: '🏪', action: 'cmd', value: 'marketplace seznam' },
  { id: 'updates',     label: 'Zkontrolovat aktualizace', icon: '⬆', action: 'cmd', value: 'zkontroluj aktualizace pluginů' },
]

function fuzzyMatch(query, label) {
  if (!query) return true
  const q = query.toLowerCase()
  const l = label.toLowerCase()
  // Exact substring
  if (l.includes(q)) return true
  // Char sequence
  let qi = 0
  for (let i = 0; i < l.length && qi < q.length; i++) {
    if (l[i] === q[qi]) qi++
  }
  return qi === q.length
}

export default function CommandPalette({ open, onClose, onNavigate, onModelChange }) {
  const [query, setQuery]   = useState('')
  const [cursor, setCursor] = useState(0)
  const inputRef = useRef()
  const sendCmd  = useJarvis(s => s.sendCommand)
  const clearMsgs= useJarvis(s => s.clearMessages)

  const filtered = COMMANDS.filter(c => fuzzyMatch(query, c.label))

  useEffect(() => {
    if (open) {
      setQuery(''); setCursor(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  useEffect(() => { setCursor(0) }, [query])

  const execute = useCallback((cmd) => {
    onClose()
    if (cmd.action === 'nav')   { onNavigate(cmd.value); return }
    if (cmd.action === 'model') { onModelChange(cmd.value); return }
    if (cmd.action === 'clear') { clearMsgs(); return }
    if (cmd.action === 'cmd')   { sendCmd(cmd.value); return }
  }, [onClose, onNavigate, onModelChange, clearMsgs, sendCmd])

  const onKeyDown = (e) => {
    if (e.key === 'Escape') { onClose(); return }
    if (e.key === 'ArrowDown') { e.preventDefault(); setCursor(c => Math.min(c+1, filtered.length-1)) }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setCursor(c => Math.max(c-1, 0)) }
    if (e.key === 'Enter' && filtered[cursor]) { execute(filtered[cursor]) }
  }

  if (!open) return null

  return (
    <>
      {/* Backdrop */}
      <div onClick={onClose} style={{
        position:'fixed', inset:0, background:'rgba(0,0,0,.6)',
        backdropFilter:'blur(4px)', zIndex:1000,
      }} />
      {/* Palette */}
      <div style={{
        position:'fixed', top:'20%', left:'50%', transform:'translateX(-50%)',
        width: Math.min(600, window.innerWidth - 32),
        background:'rgba(6,14,28,.95)',
        border:'1px solid rgba(0,212,255,.3)',
        borderRadius:12,
        boxShadow:'0 0 60px rgba(0,212,255,.15), 0 24px 60px rgba(0,0,0,.6)',
        zIndex:1001,
        overflow:'hidden',
        animation:'fadeUp .15s ease-out',
      }}>
        {/* Input */}
        <div style={{ display:'flex', alignItems:'center', gap:10, padding:'12px 16px',
          borderBottom:'1px solid rgba(0,212,255,.1)' }}>
          <span style={{ color:'var(--cyan)', fontSize:16 }}>⌘</span>
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Hledej příkazy..."
            style={{
              flex:1, background:'transparent', border:'none', outline:'none',
              color:'var(--text)', fontSize:14, fontFamily:'var(--font-ui)',
            }}
          />
          <span style={{ fontFamily:'var(--font-mono)', fontSize:10, color:'var(--text2)',
            padding:'2px 6px', border:'1px solid var(--border)', borderRadius:4 }}>ESC</span>
        </div>
        {/* Results */}
        <div style={{ maxHeight:360, overflowY:'auto' }}>
          {filtered.length === 0 && (
            <div style={{ padding:'20px 16px', textAlign:'center', color:'var(--text2)',
              fontFamily:'var(--font-mono)', fontSize:11 }}>
              Žádné výsledky
            </div>
          )}
          {filtered.map((cmd, i) => (
            <div key={cmd.id} onClick={() => execute(cmd)}
              style={{
                display:'flex', alignItems:'center', gap:12,
                padding:'10px 16px', cursor:'pointer',
                background: i === cursor ? 'rgba(0,212,255,.08)' : 'transparent',
                borderLeft: i === cursor ? '2px solid var(--cyan)' : '2px solid transparent',
                transition:'all .1s',
              }}
              onMouseEnter={() => setCursor(i)}>
              <span style={{ fontSize:16, width:24, textAlign:'center' }}>{cmd.icon}</span>
              <span style={{ flex:1, fontSize:13, color: i===cursor ? 'var(--text)' : 'var(--text2)' }}>
                {cmd.label}
              </span>
              <span style={{ fontFamily:'var(--font-mono)', fontSize:9, color:'var(--text2)',
                padding:'1px 5px', border:'1px solid var(--border)', borderRadius:3 }}>
                {cmd.action === 'nav' ? 'TAB' : cmd.action === 'model' ? 'MODEL' :
                 cmd.action === 'cmd' ? 'CMD' : 'ACTION'}
              </span>
            </div>
          ))}
        </div>
        {/* Footer */}
        <div style={{ padding:'8px 16px', borderTop:'1px solid rgba(0,212,255,.06)',
          display:'flex', gap:16, fontSize:10, color:'var(--text2)', fontFamily:'var(--font-mono)' }}>
          <span>↑↓ navigace</span>
          <span>↵ spustit</span>
          <span>ESC zavřít</span>
        </div>
      </div>
    </>
  )
}
