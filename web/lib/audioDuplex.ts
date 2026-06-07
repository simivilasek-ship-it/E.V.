/**
 * Duplex voice — mic PCM16 16kHz → /ws/audio → transcript + response + TTS playback
 */

const SAMPLE_RATE = 16000
/** RMS energy threshold for local barge-in during TTS playback */
const BARGE_IN_RMS = 0.02

function downsampleTo16k(input: Float32Array, inputRate: number): Int16Array {
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

function pcmRms(input: Float32Array): number {
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

  constructor(
    private wsUrl: string,
    private cb: DuplexCallbacks = {},
  ) {}

  get isActive() {
    return this.active
  }

  async start(): Promise<boolean> {
    if (this.active) return true
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
      })
    } catch {
      this.cb.onError?.('Mikrofon zamítnut — povol přístup v prohlížeči')
      return false
    }

    return new Promise((resolve) => {
      let opened = false
      const ws = new WebSocket(this.wsUrl)
      ws.binaryType = 'arraybuffer'
      this.ws = ws

      const fail = (msg: string) => {
        this.cb.onError?.(msg)
        this.stop()
        resolve(false)
      }

      ws.onopen = () => {
        opened = true
        ws.send(JSON.stringify({ type: 'start' }))
        this._startCapture()
        this.active = true
        this.cb.onListening?.()
        resolve(true)
      }

      ws.onmessage = async (ev) => {
        if (typeof ev.data === 'string') {
          try {
            const msg = JSON.parse(ev.data)
            if (msg.type === 'transcript' && msg.text) {
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
                this.cb.onIdle?.()
              }
            } else if (msg.type === 'tts_cancel') {
              this.abortTts()
            } else if (msg.type === 'error') {
              fail(msg.data || 'Audio WS chyba')
            } else if (msg.type === 'vad' && msg.speech) {
              this.cb.onListening?.()
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
        if (!opened) fail('Audio WS se nepřipojil — zkontroluj backend')
        else this.stop()
      }

      setTimeout(() => {
        if (!opened && ws.readyState !== WebSocket.OPEN) {
          fail('Audio WS timeout')
        }
      }, 8000)
    })
  }

  stop() {
    this.active = false
    this.abortTts(false)
    this.processor?.disconnect()
    this.source?.disconnect()
    this.processor = null
    this.source = null
    this.stream?.getTracks().forEach(t => t.stop())
    this.stream = null
    if (this.ctx?.state !== 'closed') {
      this.ctx?.close().catch(() => {})
    }
    this.ctx = null
    if (this.ws?.readyState === WebSocket.OPEN) {
      try { this.ws.send(JSON.stringify({ type: 'stop' })) } catch { /* */ }
      this.ws.close()
    }
    this.ws = null
    this.cb.onIdle?.()
  }

  /** Stop TTS playback immediately and clear queued audio. */
  abortTts(notify = true) {
    this.ttsAbort = true
    this.ttsQueue = []
    this.bargeInSent = false
    try { this.currentSource?.stop() } catch { /* already stopped */ }
    this.currentSource = null
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

      if (this.playingTts && !this.bargeInSent) {
        const energy = pcmRms(input)
        if (energy >= BARGE_IN_RMS) {
          this.bargeInSent = true
          try { this.ws!.send(JSON.stringify({ type: 'interrupt' })) } catch { /* */ }
          this.abortTts()
        }
      }

      const pcm = downsampleTo16k(input, this.ctx!.sampleRate)
      this.ws!.send(pcm.buffer)
    }
    this.source.connect(this.processor)
    this.processor.connect(this.ctx.destination)
  }

  private async _playTtsQueue() {
    if (this.playingTts || !this.ttsQueue.length || this.ttsAbort) return
    this.playingTts = true
    this.bargeInSent = false
    const ctx = new AudioContext()
    this.playbackCtx = ctx
    try {
      for (const buf of this.ttsQueue) {
        if (this.ttsAbort) break
        const audioBuf = await ctx.decodeAudioData(buf.slice(0))
        if (this.ttsAbort) break
        await new Promise<void>((resolve) => {
          const src = ctx.createBufferSource()
          src.buffer = audioBuf
          src.connect(ctx.destination)
          this.currentSource = src
          src.onended = () => {
            if (this.currentSource === src) this.currentSource = null
            resolve()
          }
          src.start()
        })
      }
    } catch {
      /* TTS playback optional */
    } finally {
      this.ttsQueue = []
      this.playingTts = false
      this.currentSource = null
      this.playbackCtx = null
      ctx.close().catch(() => {})
    }
  }
}
