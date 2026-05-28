import { create } from 'zustand'

export const useJarvis = create((set, get) => ({
  // State
  orbState: 'idle',        // idle | listening | thinking | speaking
  messages: [],
  logs: [],
  system: { cpu: 0, ram: 0, disk: 0 },
  agents: [],
  plugins: [],
  isConnected: false,
  isMicActive: false,

  // WebSocket
  ws: null,

  connect() {
    const ws = new WebSocket(`ws://${window.location.hostname}:8002/ws/logs`)
    ws.onopen    = () => set({ isConnected: true, ws })
    ws.onclose   = () => { set({ isConnected: false, ws: null }); setTimeout(() => get().connect(), 3000) }
    ws.onmessage = (e) => {
      const line = e.data
      set(s => ({ logs: [...s.logs.slice(-200), { text: line, ts: Date.now() }] }))
    }
    set({ ws })
  },

  disconnect() { get().ws?.close() },

  addMessage(text, sender) {
    set(s => ({ messages: [...s.messages, { text, sender, ts: Date.now(), id: Math.random() }] }))
  },

  setOrbState(state) { set({ orbState: state }) },
  setSystem(data)    { set({ system: data }) },
  setAgents(data)    { set({ agents: data }) },
  setPlugins(data)   { set({ plugins: data }) },
  clearMessages()    { set({ messages: [] }) },
  clearLogs()        { set({ logs: [] }) },

  async sendCommand(text) {
    if (!text.trim()) return
    get().addMessage(text, 'user')
    get().setOrbState('thinking')
    try {
      const r = await fetch('http://localhost:8002/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: text }),
      })
      const data = await r.json()
      get().addMessage(data.response || data.result || 'OK', 'jarvis')
    } catch (e) {
      get().addMessage(`Chyba: ${e.message}`, 'jarvis')
    } finally {
      get().setOrbState('idle')
    }
  },

  async fetchSystem() {
    try {
      const r = await fetch('http://localhost:8002/api/system')
      get().setSystem(await r.json())
    } catch {}
  },

  async fetchAgents() {
    try {
      const r = await fetch('http://localhost:8002/api/agents')
      get().setAgents(await r.json())
    } catch {}
  },

  async fetchPlugins() {
    try {
      const r = await fetch('http://localhost:8002/api/plugins')
      const data = await r.json()
      get().setPlugins(data.plugins || [])
    } catch {}
  },
}))
