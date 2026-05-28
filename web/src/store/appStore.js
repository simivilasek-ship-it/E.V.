import { create } from 'zustand'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8002'
const WS  = API.replace('http', 'ws')

export const useAppStore = create((set, get) => ({
  // State
  messages: [],
  input: '',
  thinking: false,
  connected: false,
  ollama: false,
  model: '—',
  cpu: 0, ram: 0, disk: 0,
  ws: null,

  // Actions
  setInput: (v) => set({ input: v }),

  fetchStatus: async () => {
    try {
      const r = await fetch(`${API}/api/status`)
      const d = await r.json()
      set({ ollama: d.ollama, model: d.model || '—' })
    } catch {}
  },

  fetchSystem: async () => {
    try {
      const r = await fetch(`${API}/api/system`)
      const d = await r.json()
      set({ cpu: d.cpu, ram: d.ram, disk: d.disk })
    } catch {}
  },

  connectWS: () => {
    const { ws } = get()
    if (ws) return
    const socket = new WebSocket(`${WS}/ws/chat`)
    socket.onopen = () => set({ connected: true, ws: socket })
    socket.onclose = () => set({ connected: false, ws: null })
    socket.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.type === 'chunk') {
        set(s => {
          const msgs = [...s.messages]
          const last = msgs[msgs.length - 1]
          if (last?.role === 'jarvis' && last.streaming) {
            msgs[msgs.length - 1] = { ...last, text: last.text + data.text }
          } else {
            msgs.push({ role: 'jarvis', text: data.text, streaming: true, id: Date.now() })
          }
          return { messages: msgs, thinking: false }
        })
      } else if (data.type === 'done') {
        set(s => {
          const msgs = [...s.messages]
          const last = msgs[msgs.length - 1]
          if (last?.streaming) msgs[msgs.length - 1] = { ...last, streaming: false }
          return { messages: msgs }
        })
      } else if (data.type === 'error') {
        set(s => ({ messages: [...s.messages,
          { role: 'jarvis', text: '⚠ ' + data.text, id: Date.now() }], thinking: false }))
      }
    }
    set({ ws: socket })
  },

  sendMessage: (text) => {
    if (!text.trim()) return
    const { ws } = get()
    set(s => ({ messages: [...s.messages, { role: 'user', text, id: Date.now() }],
                input: '', thinking: true }))
    if (ws && ws.readyState === 1) {
      ws.send(JSON.stringify({ text }))
    } else {
      // Fallback REST
      fetch(`${API}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      }).then(r => r.json()).then(d => {
        set(s => ({ messages: [...s.messages,
          { role: 'jarvis', text: d.response, id: Date.now() }], thinking: false }))
      }).catch(() => {
        set(s => ({ messages: [...s.messages,
          { role: 'jarvis', text: 'Backend nedostupný.', id: Date.now() }], thinking: false }))
      })
    }
  },
}))
