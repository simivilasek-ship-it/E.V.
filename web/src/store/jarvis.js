import { create } from 'zustand'

const API    = 'http://localhost:8002'
const WS_URL = 'ws://localhost:8002'
const MAX_ATTEMPTS = 5

// Exponential backoff: 1s, 2s, 4s, 8s, 16s — pak stop
function backoff(attempt) {
  return Math.min(1000 * Math.pow(2, attempt), 16000)
}

export const useJarvis = create((set, get) => ({
  orbState:    'idle',
  messages:    [],
  logs:        [],
  toasts:      [],
  system:      { cpu: 0, ram: 0, disk: 0 },
  agents:      [],
  plugins:     [],
  isConnected: false,
  connStatus:  'disconnected', // disconnected | connecting | connected | error | failed
  connError:   null,           // null nebo chybová zpráva pro UI
  isMicActive: false,

  _ws:       null,
  _attempt:  0,
  _retryId:  null,
  _metricsWs: null,
  _chatWs:   null,   // persistent chat WebSocket

  // ── Health check před WebSocket ──────────────────────

  async checkBackend() {
    try {
      const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(3000) })
      if (r.ok) {
        const d = await r.json()
        return d.ws === 'running'
      }
    } catch {}
    return false
  },

  // ── WebSocket logy ───────────────────────────────────

  async connect() {
    const { _ws, _attempt } = get()
    if (_ws?.readyState === WebSocket.OPEN) return

    // Max pokusů
    if (_attempt >= MAX_ATTEMPTS) {
      set({
        connStatus: 'failed',
        connError:  `Backend na ${API} nedostupný po ${MAX_ATTEMPTS} pokusech. Spusť: python dashboard.py`,
      })
      return
    }

    // Health check — ověří že backend vůbec běží
    if (_attempt === 0) {
      set({ connStatus: 'connecting', connError: null })
      const backendUp = await get().checkBackend()
      if (!backendUp) {
        set({
          connStatus: 'error',
          connError: `Backend není dostupný na ${API}. Spusť: python dashboard.py`,
        })
        get()._scheduleReconnect()
        return
      }
    }

    set({ connStatus: 'connecting', connError: null })

    let ws
    try {
      ws = new WebSocket(`${WS_URL}/ws/logs`)
    } catch (e) {
      set({ connStatus: 'error', connError: String(e) })
      get()._scheduleReconnect()
      return
    }

    const timeout = setTimeout(() => {
      if (ws.readyState !== WebSocket.OPEN) {
        ws.close()
        set({ connStatus: 'error', connError: 'Připojení vypršelo (10s)' })
        get()._scheduleReconnect()
      }
    }, 10000)

    ws.onopen = () => {
      clearTimeout(timeout)
      set({ isConnected: true, connStatus: 'connected', _ws: ws, _attempt: 0, connError: null })
      get().addToast('WebSocket připojen', 'success', 2000)
      // Spusť metriky WebSocket
      get().connectMetrics()
    }

    ws.onclose = (ev) => {
      clearTimeout(timeout)
      set({ isConnected: false, connStatus: 'disconnected', _ws: null })
      get().addToast('WebSocket odpojen', 'warning', 3000)
      if (ev.code !== 1000) get()._scheduleReconnect()
    }

    ws.onerror = () => {
      clearTimeout(timeout)
      set({ connStatus: 'error' })
    }

    ws.onmessage = (e) => {
      if (e.data === '{"type":"ping"}') return  // ignore keep-alive
      set(s => ({ logs: [...s.logs.slice(-300), { text: e.data, ts: Date.now() }] }))
    }

    set({ _ws: ws })
  },

  _scheduleReconnect() {
    const { _retryId, _attempt } = get()
    if (_retryId || _attempt >= MAX_ATTEMPTS) return
    const delay = backoff(_attempt)
    const id = setTimeout(() => {
      set(s => ({ _retryId: null, _attempt: s._attempt + 1 }))
      get().connect()
    }, delay)
    set({ _retryId: id, connStatus: 'connecting' })
  },

  disconnect() {
    const { _ws, _retryId, _metricsWs } = get()
    if (_retryId) { clearTimeout(_retryId); set({ _retryId: null }) }
    _ws?.close(1000)
    _metricsWs?.close(1000)
    set({ isConnected: false, connStatus: 'disconnected', _ws: null, _metricsWs: null, _attempt: 0 })
  },

  retry() {
    set({ _attempt: 0, connError: null })
    get().connect()
  },

  // ── /ws/agents — real-time metriky ───────────────────

  connectMetrics() {
    const { _metricsWs } = get()
    if (_metricsWs?.readyState === WebSocket.OPEN) return
    let ws
    try { ws = new WebSocket(`${WS_URL}/ws/agents`) } catch { return }
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data)
        if (d.type === 'metrics') get().setSystem({ cpu: d.cpu, ram: d.ram, disk: d.disk })
      } catch {}
    }
    ws.onclose = () => {
      set({ _metricsWs: null })
      // Reconnect metrics pouze pokud hlavní WS je connected
      if (get().isConnected) setTimeout(() => get().connectMetrics(), 5000)
    }
    set({ _metricsWs: ws })
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

  addToast(message, type = 'info', duration = 4000) {
    const id = Date.now()
    set(s => ({ toasts: [...s.toasts, { id, message, type, duration }] }))
    setTimeout(() => get().removeToast(id), duration)
  },

  removeToast(id) {
    set(s => ({ toasts: s.toasts.filter(t => t.id !== id) }))
  },

  setOrbState(s)  { set({ orbState: s }) },
  setSystem(data) { set({ system: data }) },
  setAgents(data) { set({ agents: data }) },
  setPlugins(data){ set({ plugins: data }) },
  clearMessages() { set({ messages: [] }) },
  clearLogs()     { set({ logs: [] }) },

  // ── Příkazy ──────────────────────────────────────────

  // Otevře persistent chat WebSocket (voláme jednou při startu)
  connectChat() {
    const existing = get()._chatWs
    if (existing && existing.readyState <= WebSocket.OPEN) return
    const ws = new WebSocket(`${WS_URL}/ws/chat`)
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'chunk') {
          get().setOrbState('speaking')
          set(s => {
            const msgs = [...s.messages]
            const last = msgs[msgs.length - 1]
            if (last?.streaming) msgs[msgs.length - 1] = { ...last, text: last.text + (msg.text || msg.data || '') }
            return { messages: msgs }
          })
        } else if (msg.type === 'done') {
          set(s => {
            const msgs = [...s.messages]
            const last = msgs[msgs.length - 1]
            if (last?.streaming) msgs[msgs.length - 1] = { ...last, streaming: false }
            return { messages: msgs }
          })
          get().setOrbState('idle')
        } else if (msg.type === 'error') {
          get().updateLastMessage({ text: `⚠ ${msg.text || msg.data}`, streaming: false, error: true })
          get().setOrbState('idle')
        }
      } catch {}
    }
    ws.onclose = () => {
      set({ _chatWs: null })
      // Reconnect po 2s pokud nebyla záměrně zavřena
      setTimeout(() => get().connectChat(), 2000)
    }
    set({ _chatWs: ws })
  },

  async sendCommand(text) {
    if (!text?.trim()) return
    get().addMessage(text, 'user')
    get().addMessage('', 'jarvis', { streaming: true })
    get().setOrbState('thinking')

    const chatWs = get()._chatWs
    if (chatWs && chatWs.readyState === WebSocket.OPEN) {
      chatWs.send(JSON.stringify({ command: text, text }))
      return
    }

    // REST fallback pokud WS není dostupný
    get().addToast('Chyba odpovědi — zkouším REST fallback', 'warning')
    try {
      const r = await fetch(`${API}/api/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: text }),
      })
      const data = await r.json()
      get().updateLastMessage({ text: data.response || 'OK', streaming: false })
    } catch (e) {
      get().updateLastMessage({ text: `Chyba: ${e.message}`, streaming: false, error: true })
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

  // REST fallback pro system
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
