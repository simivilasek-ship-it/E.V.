'use client'
import { create } from 'zustand'

export type ConnStatus = 'disconnected' | 'connecting' | 'connected' | 'error' | 'failed'
export type OrbState   = 'idle' | 'listening' | 'thinking' | 'speaking'

export interface Message {
  id: string
  text: string
  sender: 'user' | 'jarvis'
  ts: number
  streaming?: boolean
  error?: boolean
}

export interface SystemMetrics {
  cpu: number; ram: number; disk: number
  cpu_temp: number | null
  net: { recv: number; sent: number } | null
  gpu: { usage: number | null; vram: number | null; name: string | null } | null
  ram_gb?: number; ram_total?: number
}

export interface PendingConfirm {
  id: string
  action: string
  params: Record<string, unknown>
  timeout_s?: number
}

interface JarvisState {
  // Connection
  orbState:    OrbState
  messages:    Message[]
  logs:        Array<{ text: string; ts: number }>
  toasts:      Array<{ id: number; message: string; type: string; duration: number }>
  system:      SystemMetrics
  agents:      Record<string, unknown>
  plugins:     unknown[]
  currentModel: string
  isConnected: boolean
  connStatus:  ConnStatus
  connError:   string | null
  isMicActive: boolean
  pendingConfirm: PendingConfirm | null
  quickActionHistory: string[]

  // Internal
  _ws:        WebSocket | null
  _attempt:   number
  _retryId:   ReturnType<typeof setTimeout> | null
  _metricsWs: WebSocket | null
  _chatWs:    WebSocket | null
  _confirmWs: WebSocket | null
  _recognition: SpeechRecognition | null

  // Actions
  connect:        () => Promise<void>
  disconnect:     () => void
  retry:          () => void
  connectMetrics: () => void
  connectChat:    () => void
  connectConfirm: () => void
  respondConfirm: (approved: boolean) => void
  toggleMic:      () => void
  sendCommand:    (text: string) => Promise<void>
  addMessage:     (text: string, sender: 'user' | 'jarvis', extra?: Partial<Message>) => void
  updateLastMessage: (patch: Partial<Message>) => void
  clearMessages:  () => void
  clearLogs:      () => void
  addToast:       (message: string, type?: string, duration?: number) => void
  removeToast:    (id: number) => void
  setOrbState:    (s: OrbState) => void
  setSystem:      (data: Partial<SystemMetrics>) => void
  setAgents:      (data: Record<string, unknown>) => void
  setPlugins:     (data: unknown[]) => void
  setModel:       (model: string) => void
  addToQuickHistory: (cmd: string) => void
  checkBackend:   () => Promise<boolean>
  fetchSystem:    () => Promise<void>
  fetchAgents:    () => Promise<void>
  fetchPlugins:   () => Promise<void>
  _scheduleReconnect: () => void
}

const MAX_ATTEMPTS = 5
const backoff = (n: number) => Math.min(1000 * Math.pow(2, n), 16000)

const BACKEND_WS   = 'ws://127.0.0.1:8002'
const BACKEND_HTTP = 'http://127.0.0.1:8002'

const getWsBase = () => {
  if (typeof window === 'undefined') return BACKEND_WS
  const { hostname, protocol } = window.location
  const wsProto = protocol === 'https:' ? 'wss' : 'ws'
  // V produkci FastAPI servíruje web — WS jde na stejný host/port
  if (process.env.NODE_ENV === 'production') {
    const prodPort = window.location.port ? ':' + window.location.port : ''
    return `${wsProto}://${hostname}${prodPort}`
  }
  // Dev: Next.js rewrites NEFUNGUJÍ pro WS → připoj se přímo na backend
  return BACKEND_WS
}

const getApiBase = () => {
  if (process.env.NODE_ENV === 'production') return ''
  return BACKEND_HTTP  // Dev: jdi přímo na backend (CORS povolen)
}

export const useJarvis = create<JarvisState>((set, get) => ({
  orbState: 'idle', messages: [], logs: [], toasts: [],
  system: { cpu: 0, ram: 0, disk: 0, cpu_temp: null, net: null, gpu: null },
  agents: {}, plugins: [], currentModel: '',
  isConnected: false, connStatus: 'disconnected', connError: null, isMicActive: false,
  pendingConfirm: null,
  quickActionHistory: [],
  _ws: null, _attempt: 0, _retryId: null, _metricsWs: null, _chatWs: null, _confirmWs: null,
  _recognition: null,

  async checkBackend() {
    try {
      const r = await fetch(`${getApiBase()}/health`, { signal: AbortSignal.timeout(3000) })
      if (r.ok) { const d = await r.json(); return d.ws === 'running' }
    } catch {}
    return false
  },

  async connect() {
    const { _ws, _attempt } = get()
    if (_ws?.readyState === WebSocket.OPEN) return
    if (_attempt >= MAX_ATTEMPTS) {
      set({ connStatus: 'failed', connError: `Backend nedostupný po ${MAX_ATTEMPTS} pokusech. Spusť: python dashboard.py` })
      return
    }
    if (_attempt === 0) {
      set({ connStatus: 'connecting', connError: null })
      const up = await get().checkBackend()
      if (!up) {
        set({ connStatus: 'error', connError: 'Backend není dostupný. Spusť: python dashboard.py' })
        get()._scheduleReconnect(); return
      }
    }
    set({ connStatus: 'connecting', connError: null })
    let ws: WebSocket
    try { ws = new WebSocket(`${getWsBase()}/ws/logs`) }
    catch (e) { set({ connStatus: 'error', connError: String(e) }); get()._scheduleReconnect(); return }

    const timeout = setTimeout(() => {
      if (ws.readyState !== WebSocket.OPEN) {
        ws.close(); set({ connStatus: 'error', connError: 'Připojení vypršelo (10s)' })
        get()._scheduleReconnect()
      }
    }, 10000)

    ws.onopen = () => {
      clearTimeout(timeout)
      set({ isConnected: true, connStatus: 'connected', _ws: ws, _attempt: 0, connError: null })
      get().addToast('WebSocket připojen', 'success', 2000)
      get().connectMetrics()
    }
    ws.onclose = (ev) => {
      clearTimeout(timeout)
      set({ isConnected: false, connStatus: 'disconnected', _ws: null })
      if (ev.code !== 1000) get()._scheduleReconnect()
    }
    ws.onerror = () => { clearTimeout(timeout); set({ connStatus: 'error' }) }
    ws.onmessage = (e) => {
      if (e.data === '{"type":"ping"}') return
      set(s => ({ logs: [...s.logs.slice(-300), { text: e.data, ts: Date.now() }] }))
    }
    set({ _ws: ws })
  },

  _scheduleReconnect() {
    const { _retryId, _attempt } = get()
    if (_retryId || _attempt >= MAX_ATTEMPTS) return
    const id = setTimeout(() => {
      set(s => ({ _retryId: null, _attempt: s._attempt + 1 }))
      get().connect()
    }, backoff(_attempt))
    set({ _retryId: id, connStatus: 'connecting' })
  },

  disconnect() {
    const { _ws, _retryId, _metricsWs } = get()
    if (_retryId) { clearTimeout(_retryId); set({ _retryId: null }) }
    _ws?.close(1000); _metricsWs?.close(1000)
    set({ isConnected: false, connStatus: 'disconnected', _ws: null, _metricsWs: null, _attempt: 0 })
  },

  retry() { set({ _attempt: 0, connError: null }); get().connect() },

  connectMetrics() {
    const { _metricsWs } = get()
    if (_metricsWs?.readyState === WebSocket.OPEN) return
    let ws: WebSocket
    try { ws = new WebSocket(`${getWsBase()}/ws/agents`) } catch { return }
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data)
        if (d.type === 'metrics') get().setSystem({
          cpu: d.cpu, ram: d.ram, disk: d.disk,
          cpu_temp: d.cpu_temp ?? null,
          net: d.net_recv !== undefined ? { recv: d.net_recv, sent: d.net_sent } : get().system.net,
          gpu: d.gpu ?? get().system.gpu,
        })
      } catch {}
    }
    ws.onclose = () => {
      set({ _metricsWs: null })
      if (get().isConnected) setTimeout(() => get().connectMetrics(), 5000)
    }
    set({ _metricsWs: ws })
  },

  connectConfirm() {
    const existing = get()._confirmWs
    if (existing && existing.readyState <= WebSocket.OPEN) return
    let ws: WebSocket
    try { ws = new WebSocket(`${getWsBase()}/ws/confirm`) } catch { return }
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'confirm_request') {
          set({
            pendingConfirm: {
              id: msg.id,
              action: msg.action,
              params: msg.params || {},
              timeout_s: msg.timeout_s,
            },
          })
        } else if (msg.type === 'confirm_resolved' || msg.type === 'confirm_timeout') {
          set({ pendingConfirm: null })
        }
      } catch {}
    }
    ws.onclose = () => {
      set({ _confirmWs: null })
      if (get().isConnected) setTimeout(() => get().connectConfirm(), 3000)
    }
    set({ _confirmWs: ws })
  },

  respondConfirm(approved: boolean) {
    const pending = get().pendingConfirm
    if (!pending) return
    const payload = JSON.stringify({ type: 'confirm_response', id: pending.id, approved })
    const ws = get()._confirmWs
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(payload)
    } else {
      fetch(`${getApiBase()}/api/confirm/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: pending.id, approved }),
      }).catch(() => {})
    }
    set({ pendingConfirm: null })
  },

  connectChat() {
    const existing = get()._chatWs
    if (existing && existing.readyState <= WebSocket.OPEN) return
    const ws = new WebSocket(`${getWsBase()}/ws/chat`)
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
    ws.onclose = () => { set({ _chatWs: null }); setTimeout(() => get().connectChat(), 2000) }
    set({ _chatWs: ws })
  },

  async sendCommand(text) {
    if (!text?.trim()) return
    get().addMessage(text, 'user')
    get().addMessage('', 'jarvis', { streaming: true })
    get().setOrbState('thinking')

    const chatWs = get()._chatWs
    if (chatWs?.readyState === WebSocket.OPEN) {
      chatWs.send(JSON.stringify({ command: text, text }))
      return
    }

    // REST fallback — WebSocket nedostupný
    try {
      const r = await fetch(`${getApiBase()}/api/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      if (!r.ok) throw new Error(`Backend ${r.status}: ${r.statusText}`)
      const ct = r.headers.get('content-type') ?? ''
      if (!ct.includes('application/json')) {
        throw new Error('Backend nevrátil JSON — zkontroluj zda backend běží na :8002')
      }
      const d = await r.json()
      get().updateLastMessage({ text: d.response || 'OK', streaming: false })
    } catch (e: unknown) {
      const msg = (e as Error).message
      get().updateLastMessage({
        text: `Backend nedostupný. Spusť: \`python jarvis.py\`\n\n_${msg}_`,
        streaming: false, error: true,
      })
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

  addMessage(text, sender, extra = {}) {
    set(s => ({ messages: [...s.messages, { text, sender, ts: Date.now(), id: `${Date.now()}-${Math.random()}`, ...extra }] }))
  },
  updateLastMessage(patch) {
    set(s => { const msgs = [...s.messages]; if (msgs.length) msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], ...patch }; return { messages: msgs } })
  },
  clearMessages() { set({ messages: [] }) },
  clearLogs()     { set({ logs: [] }) },
  addToast(message, type = 'info', duration = 4000) {
    const id = Date.now()
    set(s => ({ toasts: [...s.toasts, { id, message, type, duration }] }))
    setTimeout(() => get().removeToast(id), duration)
  },
  removeToast(id) { set(s => ({ toasts: s.toasts.filter(t => t.id !== id) })) },
  setOrbState(s)  { set({ orbState: s }) },
  setSystem(data) { set(s => ({ system: { ...s.system, ...data } })) },
  setAgents(data) { set({ agents: data }) },
  setPlugins(data){ set({ plugins: data }) },
  setModel(model) { set({ currentModel: model }) },
  addToQuickHistory(cmd) {
    set(s => ({ quickActionHistory: [cmd, ...s.quickActionHistory.filter(c => c !== cmd)].slice(0, 10) }))
  },
  async fetchSystem() {
    try { get().setSystem(await fetch(`${getApiBase()}/api/system`).then(r => r.json())) } catch {}
  },
  async fetchAgents() {
    try {
      const d = await fetch(`${getApiBase()}/api/agents`).then(r => r.json())
      get().setAgents(d)
    } catch {}
  },
  async fetchPlugins() {
    try {
      const d = await fetch(`${getApiBase()}/api/plugins`).then(r => r.json())
      get().setPlugins(d.plugins || [])
    } catch {}
  },

  toggleMic() {
    const { isMicActive, _recognition } = get()
    if (isMicActive && _recognition) {
      _recognition.stop()
      set({ isMicActive: false, _recognition: null, orbState: 'idle' })
      return
    }

    const SR = typeof window !== 'undefined'
      ? (window.SpeechRecognition || window.webkitSpeechRecognition)
      : undefined
    if (!SR) {
      get().addToast('Hlas není podporován v tomto prohlížeči (zkus Chrome)', 'error')
      return
    }

    const rec = new SR()
    rec.lang = 'cs-CZ'
    rec.interimResults = false
    rec.maxAlternatives = 1

    rec.onstart = () => {
      set({ isMicActive: true, _recognition: rec, orbState: 'listening' })
    }
    rec.onresult = (ev: SpeechRecognitionEvent) => {
      const text = ev.results?.[0]?.[0]?.transcript?.trim()
      if (text) get().sendCommand(text)
    }
    rec.onerror = () => {
      set({ isMicActive: false, _recognition: null, orbState: 'idle' })
      get().addToast('Chyba rozpoznávání hlasu', 'error')
    }
    rec.onend = () => {
      set({ isMicActive: false, _recognition: null, orbState: 'idle' })
    }

    try {
      rec.start()
    } catch {
      get().addToast('Mikrofon nelze spustit — zkontroluj oprávnění', 'error')
    }
  },
}))
