/**
 * Duplex voice — mic PCM16 16kHz → /ws/audio → transcript + response + TTS playback
 */

const SAMPLE_RATE = 16000

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
            } else if (msg.type === 'tts_end') {
              await this._playTtsQueue()
              this.cb.onIdle?.()
            } else if (msg.type === 'error') {
              fail(msg.data || 'Audio WS chyba')
            } else if (msg.type === 'vad' && msg.speech) {
              this.cb.onListening?.()
            }
          } catch { /* ignore */ }
        } else if (ev.data instanceof ArrayBuffer) {
          this.ttsQueue.push(ev.data)
          this.cb.onSpeaking?.()
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
    this.ttsQueue = []
    this.playingTts = false
    this.cb.onIdle?.()
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
      const pcm = downsampleTo16k(input, this.ctx!.sampleRate)
      this.ws!.send(pcm.buffer)
    }
    this.source.connect(this.processor)
    this.processor.connect(this.ctx.destination)
  }

  private async _playTtsQueue() {
    if (this.playingTts || !this.ttsQueue.length) return
    this.playingTts = true
    const ctx = new AudioContext()
    try {
      for (const buf of this.ttsQueue) {
        const audioBuf = await ctx.decodeAudioData(buf.slice(0))
        await new Promise<void>((resolve) => {
          const src = ctx.createBufferSource()
          src.buffer = audioBuf
          src.connect(ctx.destination)
          src.onended = () => resolve()
          src.start()
        })
      }
    } catch {
      /* TTS playback optional */
    } finally {
      this.ttsQueue = []
      this.playingTts = false
      ctx.close().catch(() => {})
    }
  }
}
