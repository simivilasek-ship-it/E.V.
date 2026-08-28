'use client'
import { create } from 'zustand'
import { AudioDuplex } from '@/lib/audioDuplex'

export type ConnStatus = 'disconnected' | 'connecting' | 'connected' | 'error' | 'failed'
export type OrbState   = 'idle' | 'listening' | 'thinking' | 'speaking'
export type MessageMode = 'copilot' | 'akce' | 'agent'

export interface Message {
  id: string
  text: string
  sender: 'user' | 'ev'
  ts: number
  streaming?: boolean
  error?: boolean
  mode?: MessageMode
}

export function parseStatusToMode(status: string): MessageMode | null {
  if (!status) return null
  if (status.includes('🤖') || /agent/i.test(status)) return 'agent'
  if (status.includes('⚡') || /provádím/i.test(status)) return 'akce'
  if (status.includes('💬') || /copilot/i.test(status)) return 'copilot'
  return null
}

export interface AgentInfo {
  name: string
  running?: boolean
  interval?: number
  type?: string
  [key: string]: unknown
}

export function normalizeAgents(data: unknown): AgentInfo[] {
  if (Array.isArray(data)) {
    return data.map((item, i) => {
      if (item && typeof item === 'object') {
        const rec = item as Record<string, unknown>
        return { ...rec, name: String(rec.name ?? rec.type ?? `agent_${i}`) }
      }
      return { name: `agent_${i}` }
    })
  }
  if (data && typeof data === 'object') {
    return Object.entries(data as Record<string, unknown>).map(([name, v]) => {
      const rec = v && typeof v === 'object' ? (v as Record<string, unknown>) : {}
      return { ...rec, name: String(rec.name ?? name) }
    })
  }
  return []
}

export interface SystemMetrics {
  cpu: number; ram: number; disk: number
  cpu_temp: number | null
  net: { recv: number; sent: number } | null
  gpu: { usage: number | null; vram: number | null; name: string | null } | null
  ram_gb?: number; ram_total?: number
  load?: number
}

export interface PendingConfirm {
  id: string
  action: string
  params: Record<string, unknown>
  timeout_s?: number
}

interface EVState {
  // Connection
  orbState:    OrbState
  messages:    Message[]
  logs:        Array<{ text: string; ts: number }>
  toasts:      Array<{ id: number; message: string; type: string; duration: number }>
  system:      SystemMetrics
  agents:      AgentInfo[]
  plugins:     unknown[]
  currentModel: string
  isConnected: boolean
  connStatus:  ConnStatus
  connError:   string | null
  isMicActive: boolean
  micWanted: boolean
  duplexVoice: boolean
  pendingConfirm: PendingConfirm | null
  quickActionHistory: string[]
  activeInstall: {
    app: string
    progress: number
    stage: string
    method?: string
    error?: string
  } | null
  activityFeed: Array<{ id?: string; message: string; detail?: string; level?: string; time?: string; ts?: number }>
  proactiveSuggestions: Array<{ id: string; title: string; detail?: string; action?: string; action_label?: string; severity?: string }>
  workSummary: Record<string, unknown> | null

  // Internal
  _ws:        WebSocket | null
  _attempt:   number
  _retryId:   ReturnType<typeof setTimeout> | null
  _metricsWs: WebSocket | null
  _activityWs: WebSocket | null
  _chatWs:    WebSocket | null
  _confirmWs: WebSocket | null
  _recognition: SpeechRecognition | null
  _audioDuplex: AudioDuplex | null

  // Actions
  connect:        () => Promise<void>
  disconnect:     () => void
  retry:          () => void
  connectMetrics: () => void
  connectActivity: () => void
  connectChat:    () => void
  dismissSuggestion: (id: string) => void
  fetchWorkSummary: () => Promise<void>
  connectConfirm: () => void
  respondConfirm: (approved: boolean) => void
  toggleMic:      () => Promise<void>
  startMic:       () => Promise<void>
  resumeListening: () => void
  sendCommand:    (text: string) => Promise<void>
  addMessage:     (text: string, sender: 'user' | 'ev', extra?: Partial<Message>) => void
  updateLastMessage: (patch: Partial<Message>) => void
  clearMessages:  () => void
  clearLogs:      () => void
  addToast:       (message: string, type?: string, duration?: number) => void
  removeToast:    (id: number) => void
  setOrbState:    (s: OrbState) => void
  setSystem:      (data: Partial<SystemMetrics>) => void
  setAgents:      (data: AgentInfo[] | Record<string, unknown>) => void
  setPlugins:     (data: unknown[]) => void
  setModel:       (model: string) => void
  addToQuickHistory: (cmd: string) => void
  checkBackend:   () => Promise<boolean>
  fetchSystem:    () => Promise<void>
  fetchAgents:    () => Promise<void>
  fetchPlugins:   () => Promise<void>
  fetchDuplexFlag: () => Promise<void>
  cancelInstall: () => Promise<void>
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

export const useEV = create<EVState>((set, get) => ({
  orbState: 'idle', messages: [], logs: [], toasts: [],
  system: { cpu: 0, ram: 0, disk: 0, cpu_temp: null, net: null, gpu: null },
  agents: [], plugins: [], currentModel: '',
  isConnected: false, connStatus: 'disconnected', connError: null, isMicActive: false,
  micWanted: false,
  duplexVoice: false,
  pendingConfirm: null,
  quickActionHistory: [],
  activeInstall: null,
  activityFeed: [], proactiveSuggestions: [], workSummary: null,
  _ws: null, _attempt: 0, _retryId: null, _metricsWs: null, _activityWs: null,
  _chatWs: null, _confirmWs: null,
  _recognition: null, _audioDuplex: null,

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
      set({ connStatus: 'failed', connError: `Připojení selhalo po ${MAX_ATTEMPTS} pokusech. Spusť znovu: ./start.sh` })
      return
    }
    if (_attempt === 0) {
      set({ connStatus: 'connecting', connError: null })
      const up = await get().checkBackend()
      if (!up) {
        set({ connStatus: 'error', connError: 'Backend není dostupný. Spusť: python3 dashboard.py' })
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
      get().connectActivity()
      get().fetchWorkSummary()
      get().fetchDuplexFlag()
      get().fetchPlugins()
      get().fetchAgents()
      get().fetchSystem()
    }
    ws.onclose = (ev) => {
      clearTimeout(timeout)
      set({ isConnected: false, connStatus: 'disconnected', _ws: null })
      if (ev.code !== 1000) get()._scheduleReconnect()
    }
    ws.onerror = () => { clearTimeout(timeout); set({ connStatus: 'error' }) }
    ws.onmessage = (e) => {
      if (e.data === '{"type":"ping"}') return
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'install_progress' || msg.type === 'install_error') {
          const text = msg.message || `Instalace ${msg.app || '?'}: ${msg.stage || ''}`
          const isError = msg.type === 'install_error'
          const isDone = msg.stage === 'success' || isError || msg.stage === 'cancelled'
          const structured = isError && msg.error_detail
            ? `**Instalace ${msg.app} selhala**\n\n- **Důvod:** ${msg.error_detail}${msg.errors?.length ? `\n- **Detail:** ${msg.errors.join('; ')}` : ''}`
            : text
          get().addMessage(structured, 'ev', { error: isError })
          if (isError) get().addToast(msg.error_detail || text, 'error', 6000)
          else if (msg.stage === 'success') get().addToast(text, 'success', 4000)
          set(s => ({
            logs: [...s.logs.slice(-300), { text, ts: Date.now() }],
            activeInstall: isDone ? null : {
              app: msg.app || '?',
              progress: typeof msg.progress === 'number' ? msg.progress : 50,
              stage: msg.stage || '',
              method: msg.method,
              error: isError ? (msg.error_detail || text) : undefined,
            },
          }))
          return
        }
        if (msg.type === 'log' && msg.message) {
          set(s => ({ logs: [...s.logs.slice(-300), { text: msg.message, ts: Date.now() }] }))
          return
        }
      } catch {}
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
    const { _ws, _retryId, _metricsWs, _activityWs } = get()
    if (_retryId) { clearTimeout(_retryId); set({ _retryId: null }) }
    _ws?.close(1000); _metricsWs?.close(1000); _activityWs?.close(1000)
    set({ isConnected: false, connStatus: 'disconnected', _ws: null, _metricsWs: null, _activityWs: null, _attempt: 0 })
  },

  retry() { set({ _attempt: 0, connError: null }); get().connect() },

  connectActivity() {
    const { _activityWs } = get()
    if (_activityWs?.readyState === WebSocket.OPEN) return
    let ws: WebSocket
    try { ws = new WebSocket(`${getWsBase()}/ws/activity`) } catch { return }
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data)
        if (d.type === 'ping') return
        if (d.type === 'proactive') {
          set(s => ({
            proactiveSuggestions: [...s.proactiveSuggestions.filter(x => x.id !== d.id), {
              id: d.id, title: d.title, detail: d.detail, action: d.action,
              action_label: d.action_label, severity: d.severity,
            }].slice(-10),
          }))
          get().addToast(d.title, d.severity === 'error' ? 'error' : 'warning', 6000)
        } else if (d.type === 'activity') {
          set(s => ({
            activityFeed: [...s.activityFeed, {
              id: d.id || `${Date.now()}`,
              message: d.message || d.title || '',
              detail: d.detail, level: d.level || 'info',
              ts: d.ts, time: d.time || new Date().toLocaleTimeString('cs', { hour: '2-digit', minute: '2-digit' }),
            }].slice(-100),
          }))
        }
      } catch {}
    }
    ws.onclose = () => {
      set({ _activityWs: null })
      if (get().isConnected) setTimeout(() => get().connectActivity(), 5000)
    }
    set({ _activityWs: ws })
  },

  dismissSuggestion(id) {
    fetch(`${getApiBase()}/api/proactive/dismiss`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    }).catch(() => {})
    set(s => ({ proactiveSuggestions: s.proactiveSuggestions.filter(x => x.id !== id) }))
  },

  async fetchWorkSummary() {
    try {
      const d = await fetch(`${getApiBase()}/api/activity/today`).then(r => r.json())
      set({ workSummary: d.summary || null })
    } catch {}
  },

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
        } else if (msg.type === 'agent_step') {
          get().setOrbState('thinking')
          const step = msg.data || msg.text || ''
          set(s => {
            const msgs = [...s.messages]
            const last = msgs[msgs.length - 1]
            if (last?.streaming) {
              const prefix = last.text ? last.text + '\n' : ''
              msgs[msgs.length - 1] = { ...last, text: prefix + `▸ ${step}` }
            }
            return { messages: msgs }
          })
        } else if (msg.type === 'status') {
          get().setOrbState('thinking')
          const mode = parseStatusToMode(msg.data || msg.text || '')
          if (mode) {
            set(s => {
              const msgs = [...s.messages]
              for (let i = msgs.length - 1; i >= 0; i--) {
                if (msgs[i].sender === 'ev') {
                  msgs[i] = { ...msgs[i], mode }
                  break
                }
              }
              return { messages: msgs }
            })
          }
        } else if (msg.type === 'done') {
          set(s => {
            const msgs = [...s.messages]
            const last = msgs[msgs.length - 1]
            if (last?.streaming) msgs[msgs.length - 1] = { ...last, streaming: false }
            return { messages: msgs }
          })
          get().setOrbState(get().micWanted ? 'listening' : 'idle')
          const last = get().messages[get().messages.length - 1]
          if (last?.sender === 'ev' && last.text) {
            void import('@/lib/tts').then(async ({ playReplySpeech }) => {
              await playReplySpeech(last.text)
              get().resumeListening()
            })
          }
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
    get().addMessage('', 'ev', { streaming: true })
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
      if (d.response) {
        await import('@/lib/tts').then(async ({ playReplySpeech }) => {
          await playReplySpeech(d.response)
          get().resumeListening()
        })
      }
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
      get().setOrbState(get().micWanted ? 'listening' : 'idle')
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
  setAgents(data) { set({ agents: normalizeAgents(data) }) },
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

  async cancelInstall() {
    const inst = get().activeInstall
    if (!inst?.app) return
    try {
      await fetch(`${getApiBase()}/api/install/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app: inst.app }),
      })
      get().addToast(`Ruším instalaci ${inst.app}…`, 'warning', 3000)
      set({ activeInstall: null })
    } catch {
      get().addToast('Zrušení instalace selhalo', 'error', 3000)
    }
  },

  async fetchDuplexFlag() {
    try {
      const d = await fetch(`${getApiBase()}/api/status`).then(r => r.json())
      const enabled = Boolean(d?.features?.audio_duplex?.live_duplex_stt_tts)
      set({ duplexVoice: enabled })
    } catch {
      set({ duplexVoice: false })
    }
  },

  async startMic() {
    if (get().isMicActive) return
    await get().toggleMic()
  },

  resumeListening() {
    const { micWanted, _recognition } = get()
    if (!micWanted) return
    set({ isMicActive: true, orbState: 'listening' })
    if (_recognition) {
      try { _recognition.start() } catch { /* already started */ }
    }
  },

  async toggleMic() {
    const { isMicActive, _recognition, _audioDuplex, duplexVoice, micWanted } = get()

    if (isMicActive || micWanted) {
      set({ micWanted: false, isMicActive: false, orbState: 'idle' })
      try { _recognition?.stop() } catch { /* */ }
      _audioDuplex?.stop()
      set({ _recognition: null, _audioDuplex: null })
      return
    }

    set({ micWanted: true, isMicActive: true, orbState: 'listening' })

    if (duplexVoice) {
      const duplex = new AudioDuplex(`${getWsBase()}/ws/audio`, {
        onListening: () => {
          if (!get().micWanted) return
          set({ isMicActive: true, orbState: 'listening' })
        },
        onTranscript: (text) => get().addMessage(text, 'user'),
        onResponse: (text) => {
          get().addMessage(text, 'ev')
          get().setOrbState('speaking')
        },
        onSpeaking: () => get().setOrbState('speaking'),
        onIdle: () => {
          if (get().micWanted) {
            set({ isMicActive: true, orbState: 'listening' })
            return
          }
          set({ isMicActive: false, _audioDuplex: null, orbState: 'idle' })
        },
        onError: (msg) => {
          get().addToast(msg, 'error')
          if (get().micWanted) {
            set({ isMicActive: true, orbState: 'listening' })
            return
          }
          set({ isMicActive: false, _audioDuplex: null, orbState: 'idle' })
        },
      })
      set({ _audioDuplex: duplex })
      const ok = await duplex.start()
      if (ok) return
      set({ _audioDuplex: null })
      get().addToast('Duplex hlas selhal — zkouším Web Speech API', 'info')
    }

    const SR = typeof window !== 'undefined'
      ? (window.SpeechRecognition || window.webkitSpeechRecognition)
      : undefined
    if (!SR) {
      if (!get()._audioDuplex) {
        set({ micWanted: false, isMicActive: false, orbState: 'idle' })
        get().addToast('Hlas není podporován v tomto prohlížeči (zkus Chrome)', 'error')
      }
      return
    }

    const rec = new SR()
    rec.lang = 'cs-CZ'
    rec.interimResults = false
    rec.maxAlternatives = 1
    ;(rec as SpeechRecognition & { continuous?: boolean }).continuous = true

    rec.onstart = () => {
      if (!get().micWanted) return
      set({ isMicActive: true, _recognition: rec, orbState: 'listening' })
    }
    rec.onresult = (ev: SpeechRecognitionEvent) => {
      if (!get().micWanted) return
      const result = ev.results?.[ev.results.length - 1]
      if (!result?.isFinal) return
      const text = result[0]?.transcript?.trim()
      if (text) get().sendCommand(text)
    }
    rec.onerror = (ev: Event) => {
      const err = (ev as { error?: string }).error
      if (err === 'no-speech' || err === 'aborted' || err === 'network') return
      if (get().micWanted) return
      set({ isMicActive: false, _recognition: null, orbState: 'idle' })
      get().addToast('Chyba rozpoznávání hlasu', 'error')
    }
    rec.onend = () => {
      if (!get().micWanted || get()._recognition !== rec) return
      try {
        rec.start()
      } catch {
        setTimeout(() => {
          if (get().micWanted && get()._recognition === rec) {
            try { rec.start() } catch { /* */ }
          }
        }, 250)
      }
    }

    try {
      rec.start()
      set({ _recognition: rec })
    } catch {
      get().addToast('Mikrofon nelze spustit — zkontroluj oprávnění', 'error')
    }
  },
}))
