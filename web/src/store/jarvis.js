import { create } from 'zustand'

const API = 'http://localhost:8002'
const WS  = 'ws://localhost:8002'

// Exponential backoff: 1s, 2s, 4s, 8s, max 30s
function backoff(attempt) {
  return Math.min(1000 * Math.pow(2, attempt), 30000)
}

export const useJarvis = create((set, get) => ({
  orbState:    'idle',
  messages:    [],
  logs:        [],
  system:      { cpu: 0, ram: 0, disk: 0 },
  agents:      [],
  plugins:     [],
  isConnected: false,
  connStatus:  'disconnected', // disconnected | connecting | connected | error
  isMicActive: false,

  _ws:       null,
  _attempt:  0,
  _retryId:  null,

  // ── WebSocket ────────────────────────────────────────

  connect() {
    const { _ws } = get()
    if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING)) return

    set({ connStatus: 'connecting' })
    let ws
    try {
      ws = new WebSocket(`${WS}/ws/logs`)
    } catch (e) {
      get()._scheduleReconnect()
      return
    }

    ws.onopen = () => {
      set({ isConnected: true, connStatus: 'connected', _ws: ws, _attempt: 0 })
    }

    ws.onclose = (ev) => {
      set({ isConnected: false, connStatus: 'disconnected', _ws: null })
      // Don't reconnect if closed cleanly (code 1000)
      if (ev.code !== 1000) get()._scheduleReconnect()
    }

    ws.onerror = () => {
      set({ connStatus: 'error' })
    }

    ws.onmessage = (e) => {
      const text = typeof e.data === 'string' ? e.data : ''
      set(s => ({ logs: [...s.logs.slice(-300), { text, ts: Date.now() }] }))
    }

    set({ _ws: ws })
  },

  _scheduleReconnect() {
    const { _retryId, _attempt } = get()
    if (_retryId) return
    const delay = backoff(_attempt)
    const id = setTimeout(() => {
      set(s => ({ _retryId: null, _attempt: s._attempt + 1 }))
      get().connect()
    }, delay)
    set({ _retryId: id })
  },

  disconnect() {
    const { _ws, _retryId } = get()
    if (_retryId) { clearTimeout(_retryId); set({ _retryId: null }) }
    _ws?.close(1000, 'user disconnect')
    set({ isConnected: false, connStatus: 'disconnected', _ws: null, _attempt: 0 })
  },

  // ── Messages ─────────────────────────────────────────

  addMessage(text, sender, extra = {}) {
    set(s => ({
      messages: [...s.messages, {
        text, sender, ts: Date.now(),
        id: `${Date.now()}-${Math.random()}`,
        ...extra,
      }],
    }))
  },

  updateLastMessage(patch) {
    set(s => {
      const msgs = [...s.messages]
      if (msgs.length > 0) msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], ...patch }
      return { messages: msgs }
    })
  },

  setOrbState(state) { set({ orbState: state }) },
  setSystem(data)    { set({ system: data }) },
  setAgents(data)    { set({ agents: data }) },
  setPlugins(data)   { set({ plugins: data }) },
  clearMessages()    { set({ messages: [] }) },
  clearLogs()        { set({ logs: [] }) },

  // ── Commands via streaming WebSocket ─────────────────

  async sendCommand(text) {
    if (!text?.trim()) return
    get().addMessage(text, 'user')
    get().addMessage('', 'jarvis', { streaming: true })
    get().setOrbState('thinking')

    try {
      // Try streaming WebSocket first
      const chatWs = new WebSocket(`${WS}/ws/chat`)
      let resolved = false

      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => { chatWs.close(); reject(new Error('timeout')) }, 15000)

        chatWs.onopen  = () => chatWs.send(JSON.stringify({ command: text }))
        chatWs.onerror = () => { clearTimeout(timeout); reject(new Error('ws error')) }
        chatWs.onclose = () => { clearTimeout(timeout); if (!resolved) resolve() }

        chatWs.onmessage = (e) => {
          try {
            const msg = JSON.parse(e.data)
            if (msg.type === 'chunk') {
              get().setOrbState('speaking')
              set(s => {
                const msgs = [...s.messages]
                const last = msgs[msgs.length - 1]
                if (last?.streaming) msgs[msgs.length - 1] = { ...last, text: last.text + msg.data }
                return { messages: msgs }
              })
            } else if (msg.type === 'done') {
              resolved = true
              clearTimeout(timeout)
              chatWs.close()
              resolve()
            } else if (msg.type === 'error') {
              clearTimeout(timeout)
              reject(new Error(msg.data))
            }
          } catch {}
        }
      })
    } catch {
      // Fallback REST
      try {
        const r = await fetch(`${API}/api/command`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: text }),
        })
        const data = await r.json()
        get().updateLastMessage({ text: data.response || data.result || 'OK', streaming: false })
      } catch (e) {
        get().updateLastMessage({ text: `Chyba: ${e.message}`, streaming: false, error: true })
      }
    } finally {
      set(s => {
        const msgs = [...s.messages]
        const last = msgs[msgs.length - 1]
        if (last?.streaming) msgs[msgs.length - 1] = { ...last, streaming: false }
        return { messages: msgs }
      })
      get().setOrbState('idle')
    }
  },

  // ── REST fetches ─────────────────────────────────────

  async fetchSystem() {
    try { get().setSystem(await fetch(`${API}/api/system`).then(r => r.json())) } catch {}
  },
  async fetchAgents() {
    try { get().setAgents(await fetch(`${API}/api/agents`).then(r => r.json())) } catch {}
  },
  async fetchPlugins() {
    try {
      const d = await fetch(`${API}/api/plugins`).then(r => r.json())
      get().setPlugins(d.plugins || [])
    } catch {}
  },
}))
