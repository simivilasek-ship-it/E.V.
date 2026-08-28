'use client'
import { useEffect, useRef } from 'react'
import type { OrbState } from '@/store/ev'

interface JarvisCoreProps {
  state?: OrbState
}

type Vec = { x: number; y: number; z: number }

function rotY(p: Vec, a: number): Vec {
  const c = Math.cos(a), s = Math.sin(a)
  return { x: p.x * c + p.z * s, y: p.y, z: -p.x * s + p.z * c }
}
function rotX(p: Vec, a: number): Vec {
  const c = Math.cos(a), s = Math.sin(a)
  return { x: p.x, y: p.y * c - p.z * s, z: p.y * s + p.z * c }
}
function rotZ(p: Vec, a: number): Vec {
  const c = Math.cos(a), s = Math.sin(a)
  return { x: p.x * c - p.y * s, y: p.x * s + p.y * c, z: p.z }
}

function circle(n: number, tiltX = 0, tiltZ = 0): Vec[] {
  const pts: Vec[] = []
  for (let i = 0; i <= n; i++) {
    const t = (i / n) * Math.PI * 2
    pts.push(rotZ(rotX({ x: Math.cos(t), y: Math.sin(t), z: 0 }, tiltX), tiltZ))
  }
  return pts
}

function meridian(n: number, lon: number): Vec[] {
  const pts: Vec[] = []
  for (let i = 0; i <= n; i++) {
    const lat = (i / n) * Math.PI - Math.PI / 2
    pts.push({
      x: Math.cos(lat) * Math.cos(lon),
      y: Math.sin(lat),
      z: Math.cos(lat) * Math.sin(lon),
    })
  }
  return pts
}

function parallel(n: number, lat: number): Vec[] {
  const pts: Vec[] = []
  const r = Math.cos(lat)
  for (let i = 0; i <= n; i++) {
    const lon = (i / n) * Math.PI * 2
    pts.push({ x: r * Math.cos(lon), y: Math.sin(lat), z: r * Math.sin(lon) })
  }
  return pts
}

function fibonacci(count: number): Vec[] {
  const pts: Vec[] = []
  const golden = Math.PI * (3 - Math.sqrt(5))
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2
    const r = Math.sqrt(1 - y * y)
    const theta = golden * i
    pts.push({ x: Math.cos(theta) * r, y, z: Math.sin(theta) * r })
  }
  return pts
}

const RINGS = [
  circle(72, 0, 0),
  circle(64, 0.7, 0.15),
  circle(64, -0.55, 0.4),
  circle(56, 1.05, -0.3),
]
const MERIDIANS = Array.from({ length: 8 }, (_, i) => meridian(40, (i / 8) * Math.PI))
const PARALLELS = [-0.7, -0.35, 0, 0.35, 0.7].map(lat => parallel(48, lat))
const NODES = fibonacci(42)
const WIRES = [...RINGS, ...MERIDIANS, ...PARALLELS]

export default function JarvisCore({ state = 'idle' }: JarvisCoreProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const stateRef = useRef(state)
  stateRef.current = state

  useEffect(() => {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap) return
    const ctx = canvas.getContext('2d', { alpha: true })
    if (!ctx) return

    let raf = 0
    let running = true
    const t0 = performance.now()

    const resize = () => {
      const size = Math.min(wrap.clientWidth, wrap.clientHeight)
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = Math.max(1, Math.floor(size * dpr))
      canvas.height = Math.max(1, Math.floor(size * dpr))
      canvas.style.width = `${size}px`
      canvas.style.height = `${size}px`
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(wrap)

    const draw = (now: number) => {
      if (!running) return
      const st = stateRef.current
      const t = (now - t0) / 1000
      const w = canvas.width
      const h = canvas.height
      const cx = w / 2
      const cy = h / 2
      const speed = st === 'thinking' ? 0.55 : st === 'speaking' ? 0.38 : 0.18
      const pulse = st === 'speaking'
        ? 1 + 0.045 * Math.sin(t * 8)
        : st === 'listening'
          ? 1 + 0.03 * Math.sin(t * 3.2)
          : 1 + 0.018 * Math.sin(t * 1.6)
      const radius = Math.min(w, h) * 0.34 * pulse
      const ay = t * speed
      const ax = 0.32 + Math.sin(t * 0.21) * 0.08
      const dist = 3.1

      ctx.clearRect(0, 0, w, h)
      ctx.globalCompositeOperation = 'lighter'

      const bloom = ctx.createRadialGradient(cx, cy, radius * 0.05, cx, cy, radius * 2.1)
      bloom.addColorStop(0, 'rgba(210, 235, 255, 0.22)')
      bloom.addColorStop(0.22, 'rgba(56, 160, 255, 0.16)')
      bloom.addColorStop(0.5, 'rgba(30, 90, 200, 0.06)')
      bloom.addColorStop(1, 'rgba(0, 0, 0, 0)')
      ctx.fillStyle = bloom
      ctx.fillRect(0, 0, w, h)

      const project = (p: Vec) => {
        const r = rotX(rotY(p, ay), ax)
        const z = r.z + dist
        const f = dist / z
        return { x: cx + r.x * radius * f, y: cy + r.y * radius * f, z: r.z, f }
      }

      for (const wire of WIRES) {
        for (let i = 1; i < wire.length; i++) {
          const a = project(wire[i - 1])
          const b = project(wire[i])
          const z = (a.z + b.z) * 0.5
          ctx.beginPath()
          ctx.moveTo(a.x, a.y)
          ctx.lineTo(b.x, b.y)
          ctx.strokeStyle = `rgba(110, 190, 255, ${0.08 + (z + 1) * 0.28})`
          ctx.lineWidth = (z > 0 ? 1.25 : 0.5) * (w / 500)
          ctx.stroke()
        }
      }

      for (const node of NODES) {
        const p = project(node)
        const a = 0.25 + (p.z + 1) * 0.4
        const r = (1.1 + p.f * 1.6) * (w / 520)
        ctx.beginPath()
        ctx.fillStyle = `rgba(190, 230, 255, ${a})`
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2)
        ctx.fill()
      }

      const core = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius * 0.42)
      core.addColorStop(0, 'rgba(240, 250, 255, 0.55)')
      core.addColorStop(0.35, 'rgba(90, 180, 255, 0.2)')
      core.addColorStop(1, 'rgba(30, 100, 255, 0)')
      ctx.beginPath()
      ctx.fillStyle = core
      ctx.arc(cx, cy, radius * 0.42, 0, Math.PI * 2)
      ctx.fill()

      ctx.globalCompositeOperation = 'source-over'
      raf = requestAnimationFrame(draw)
    }

    raf = requestAnimationFrame(draw)
    return () => {
      running = false
      cancelAnimationFrame(raf)
      ro.disconnect()
    }
  }, [])

  return (
    <div
      ref={wrapRef}
      className="jarvis-core-wrap"
      data-testid="jarvis-core"
      aria-label={`E.V. — ${state}`}
    >
      <canvas ref={canvasRef} />
    </div>
  )
}
