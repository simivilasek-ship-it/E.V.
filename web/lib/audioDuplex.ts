/**
 * Duplex voice — mic PCM16 16kHz → /ws/audio → transcript + response + TTS playback
 */

import { subscribeTtsPlayback } from '@/lib/tts'

const SAMPLE_RATE = 16000
/** Higher threshold so her own playback isn't treated as barge-in */
const BARGE_IN_RMS = 0.12

export function downsampleTo16k(input: Float32Array, inputRate: number): Int16Array {
  if (inputRate === SAMPLE_RATE) {
    const out = new Int16Array(input.length)
    for (let i = 0; i < input.length; i++) {
      const s = Math.max(-1, Math.min(1, input[i]))
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
    return out
  }
  const ratio = inputRate / SAMPLE_RATE
  const outLen = Math.floor(input.length / ratio)
  const out = new Int16Array(outLen)
  for (let i = 0; i < outLen; i++) {
    const idx = Math.floor(i * ratio)
    const s = Math.max(-1, Math.min(1, input[idx] ?? 0))
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }
  return out
}

export function pcmRms(input: Float32Array): number {
  let sum = 0
  for (let i = 0; i < input.length; i++) {
    sum += input[i] * input[i]
  }
  return Math.sqrt(sum / Math.max(input.length, 1))
}

export type DuplexCallbacks = {
  onListening?: () => void
  onTranscript?: (text: string) => void
  onResponse?: (text: string) => void
  onSpeaking?: () => void
  onIdle?: () => void
  onError?: (msg: string) => void
}

export class AudioDuplex {
  private ws: WebSocket | null = null
  private stream: MediaStream | null = null
  private ctx: AudioContext | null = null
  private processor: ScriptProcessorNode | null = null
  private source: MediaStreamAudioSourceNode | null = null
  private active = false
  private ttsQueue: ArrayBuffer[] = []
  private playingTts = false
  private ttsAbort = false
  private bargeInSent = false
  private currentSource: AudioBufferSourceNode | null = null
  private playbackCtx: AudioContext | null = null
  private htmlAudio: HTMLAudioElement | null = null
  private wanted = false
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private externalPlayback = false
  private unsubTts: (() => void) | null = null

  constructor(
    private wsUrl: string,
    private cb: DuplexCallbacks = {},
  ) {}

  get isActive() {
    return this.active
  }

  async start(): Promise<boolean> {
    this.wanted = true
    if (!this.unsubTts) {
      this.unsubTts = subscribeTtsPlayback(playing => {
        this.externalPlayback = playing
      })
    }
    if (this.active) return true
    if (!this.stream || this.stream.getTracks().every(t => t.readyState !== 'live')) {
      try {
        this.stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
        })
      } catch {
        this.cb.onError?.('Mikrofon zamítnut — povol přístup v prohlížeči')
        return false
      }
    }

    return new Promise((resolve) => {
      let ready = false
      let settled = false
      const ws = new WebSocket(this.wsUrl)
      ws.binaryType = 'arraybuffer'
      this.ws = ws

      const fail = (msg: string) => {
        if (settled) return
        settled = true
        this.wanted = false
        this.cb.onError?.(msg)
        this._teardown(false)
        resolve(false)
      }

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'start' }))
      }

      ws.onmessage = async (ev) => {
        if (typeof ev.data === 'string') {
          try {
            const msg = JSON.parse(ev.data)
            if (msg.type === 'ready' && !ready) {
              ready = true
              settled = true
              this._startCapture()
              this.active = true
              this.cb.onListening?.()
              resolve(true)
            } else if (msg.type === 'transcript' && msg.text) {
              this.cb.onTranscript?.(msg.text)
            } else if (msg.type === 'response' && msg.text) {
              this.cb.onResponse?.(msg.text)
            } else if (msg.type === 'tts_start') {
              this.ttsAbort = false
              this.bargeInSent = false
              this.ttsQueue = []
            } else if (msg.type === 'tts_end') {
              if (!this.ttsAbort) {
                await this._playTtsQueue()
                if (this.wanted) this.cb.onListening?.()
              }
            } else if (msg.type === 'tts_cancel') {
              this.abortTts()
            } else if (msg.type === 'error') {
              if (!ready) fail(msg.data || 'Audio WS chyba')
              else this.cb.onError?.(msg.data || 'Audio WS chyba')
            } else if (msg.type === 'vad' && msg.speech) {
              if (this.wanted) this.cb.onListening?.()
            }
          } catch { /* ignore */ }
        } else if (ev.data instanceof ArrayBuffer) {
          if (!this.ttsAbort) {
            this.ttsQueue.push(ev.data)
            this.cb.onSpeaking?.()
          }
        }
      }

      ws.onerror = () => fail('WebSocket audio selhal')
      ws.onclose = () => {
        if (!ready) fail('Audio WS se nepřipojil — zkontroluj backend')
        else this._scheduleReconnect()
      }

      setTimeout(() => {
        if (!ready) fail('Audio WS timeout')
      }, 8000)
    })
  }

  stop() {
    this.wanted = false
    this.unsubTts?.()
    this.unsubTts = null
    this.externalPlayback = false
    this._teardown(true)
  }

  private _scheduleReconnect() {
    this.active = false
    this._stopCapture()
    if (!this.wanted) {
      this.cb.onIdle?.()
      return
    }
    if (this.reconnectTimer) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      if (this.wanted && !this.active) {
        void this.start()
      }
    }, 400)
  }

  private _stopCapture() {
    this.processor?.disconnect()
    this.source?.disconnect()
    this.processor = null
    this.source = null
    if (this.ctx?.state !== 'closed') {
      this.ctx?.close().catch(() => {})
    }
    this.ctx = null
  }

  private _teardown(notifyIdle: boolean) {
    this.active = false
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.abortTts(false)
    this._stopCapture()
    if (!this.wanted) {
      this.stream?.getTracks().forEach(t => t.stop())
      this.stream = null
    }
    if (this.ws) {
      this.ws.onclose = null
      this.ws.onerror = null
      this.ws.onmessage = null
      try {
        if (this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'stop' }))
        }
        this.ws.close()
      } catch { /* */ }
      this.ws = null
    }
    if (notifyIdle) this.cb.onIdle?.()
  }

  /** Stop TTS playback immediately and clear queued audio. */
  abortTts(notify = true) {
    this.ttsAbort = true
    this.ttsQueue = []
    this.bargeInSent = false
    try { this.currentSource?.stop() } catch { /* already stopped */ }
    this.currentSource = null
    try { this.htmlAudio?.pause() } catch { /* */ }
    this.htmlAudio = null
    if (this.playbackCtx?.state !== 'closed') {
      this.playbackCtx?.close().catch(() => {})
    }
    this.playbackCtx = null
    this.playingTts = false
    if (notify) this.cb.onListening?.()
  }

  private _startCapture() {
    if (!this.stream) return
    this.ctx = new AudioContext()
    this.source = this.ctx.createMediaStreamSource(this.stream)
    const bufferSize = 4096
    this.processor = this.ctx.createScriptProcessor(bufferSize, 1, 1)
    this.processor.onaudioprocess = (e) => {
      if (!this.active || this.ws?.readyState !== WebSocket.OPEN) return
      const input = e.inputBuffer.getChannelData(0)

      // Don't send her own TTS (HTML or duplex queue) back as "user speech"
      if (this.playingTts || this.externalPlayback) {
        if (this.playingTts && !this.externalPlayback) {
          const energy = pcmRms(input)
          if (energy >= BARGE_IN_RMS && !this.bargeInSent) {
            this.bargeInSent = true
            try { this.ws!.send(JSON.stringify({ type: 'interrupt' })) } catch { /* */ }
            this.abortTts()
          }
        }
        return
      }

      const pcm = downsampleTo16k(input, this.ctx!.sampleRate)
      this.ws!.send(pcm.buffer)
    }
    this.source.connect(this.processor)
    const mute = this.ctx.createGain()
    mute.gain.value = 0
    this.processor.connect(mute)
    mute.connect(this.ctx.destination)
  }

  private _sniffMime(buf: ArrayBuffer): string {
    const u = new Uint8Array(buf)
    if (u[0] === 0x52 && u[1] === 0x49 && u[2] === 0x46 && u[3] === 0x46) return 'audio/wav'
    return 'audio/mpeg'
  }

  private async _playTtsQueue() {
    if (this.playingTts || !this.ttsQueue.length || this.ttsAbort) return
    this.playingTts = true
    this.bargeInSent = false
    const mime = this._sniffMime(this.ttsQueue[0])
    const blob = new Blob(this.ttsQueue, { type: mime })
    const url = URL.createObjectURL(blob)
    try {
    const audio = new Audio(url)
    audio.preload = 'auto'
    this.htmlAudio = audio
    await new Promise<void>((resolve) => {
      const done = () => resolve()
      audio.onended = done
      audio.onerror = done
      const start = () => { audio.play().catch(done) }
      audio.oncanplaythrough = start
      audio.load()
      setTimeout(() => {
        if (this.htmlAudio === audio && audio.paused) start()
      }, 250)
    })
    } catch {
      /* TTS playback optional */
    } finally {
      URL.revokeObjectURL(url)
      this.ttsQueue = []
      this.playingTts = false
      this.currentSource = null
      this.htmlAudio = null
    }
  }
}
