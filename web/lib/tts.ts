import { apiUrl } from '@/lib/api'

let current: HTMLAudioElement | null = null
let speaking = false
type TtsListener = (playing: boolean) => void
const ttsListeners = new Set<TtsListener>()

export function isTtsPlaying(): boolean {
  return speaking
}

export function subscribeTtsPlayback(cb: TtsListener): () => void {
  ttsListeners.add(cb)
  cb(speaking)
  return () => { ttsListeners.delete(cb) }
}

function notifyTts(playing: boolean) {
  speaking = playing
  ttsListeners.forEach(fn => {
    try { fn(playing) } catch { /* ignore listener errors */ }
  })
}

export function unlockAudio(): void {
  try {
    const AC = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!AC) return
    const ctx = new AC()
    void ctx.resume()
    const buf = ctx.createBuffer(1, 1, 22050)
    const src = ctx.createBufferSource()
    src.buffer = buf
    src.connect(ctx.destination)
    src.start(0)
  } catch {
    /* unlock is best-effort */
  }
}

export async function prepareReplySpeech(text: string): Promise<HTMLAudioElement | null> {
  const spoken = (text || '').trim()
  if (!spoken || spoken.startsWith('⚠') || spoken.startsWith('Backend')) return null
  const res = await fetch(apiUrl('/api/tts/audio'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: spoken }),
  })
  if (!res.ok) return null
  const blob = await res.blob()
  if (blob.size < 32) return null
  const url = URL.createObjectURL(blob)
  const audio = new Audio(url)
  audio.preload = 'auto'
  await new Promise<void>((resolve) => {
    const done = () => resolve()
    audio.oncanplaythrough = done
    audio.load()
    setTimeout(done, 1200)
  })
  audio.dataset.blobUrl = url
  return audio
}

export async function playPreparedSpeech(audio: HTMLAudioElement): Promise<boolean> {
  notifyTts(true)
  try {
    if (current && current !== audio) current.pause()
    current = audio
    try {
      audio.currentTime = 0
    } catch {
      /* some browsers reject currentTime before metadata */
    }
    await audio.play()
    await new Promise<void>((resolve) => {
      const done = () => {
        const blobUrl = audio.dataset.blobUrl
        if (blobUrl) URL.revokeObjectURL(blobUrl)
        if (current === audio) current = null
        resolve()
      }
      audio.onended = done
      audio.onerror = done
    })
    return true
  } catch {
    notifyTts(false)
    return false
  } finally {
    notifyTts(false)
  }
}

export async function playReplySpeech(text: string): Promise<boolean> {
  try {
    const audio = await prepareReplySpeech(text)
    if (!audio) return false
    return await playPreparedSpeech(audio)
  } catch {
    return false
  }
}
