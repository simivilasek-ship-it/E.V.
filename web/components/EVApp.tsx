'use client'
import { useEffect, useState, useCallback } from 'react'
import { useEV } from '@/store/ev'
import Sidebar, { type Tab } from './Sidebar'
import ChatPanel from './ChatPanel'
import ContextSidebar from './ContextSidebar'
import ToastContainer from './Toast'
import ErrorBoundary from './ErrorBoundary'
import Spotlight from './Spotlight'
import ConfirmModal from './ConfirmModal'
import OnboardingWizard from './OnboardingWizard'
import dynamic from 'next/dynamic'
import { EVStatusBar } from './HeroPanel'
import HomePanel from './HomePanel'
import { apiUrl } from '@/lib/api'
import { playReplySpeech, unlockAudio, prepareReplySpeech, playPreparedSpeech } from '@/lib/tts'

/** One hello per page load — React Strict Mode must not replay it. */
let helloBooted = false

// Lazy load heavy panels
const SystemPanel  = dynamic(() => import('./SystemPanel'),  { ssr: false })
const DashboardPanel = dynamic(() => import('./DashboardPanel'), { ssr: false })
const PluginMarketplace = dynamic(() => import('./PluginMarketplace'), { ssr: false })
const AgentGraphV2 = dynamic(() => import('./AgentGraphV2'), { ssr: false })
const AgentTimeline = dynamic(() => import('./AgentTimeline'), { ssr: false })
const MemoryGraph  = dynamic(() => import('./MemoryGraph'),  { ssr: false })
const SkillGenerator = dynamic(() => import('./SkillGenerator'), { ssr: false })
const WorkflowEditor = dynamic(() => import('./WorkflowEditor'), { ssr: false })
const SettingsPanel  = dynamic(() => import('./SettingsPanel'),  { ssr: false })
const MissionPanel   = dynamic(() => import('./MissionPanel'), { ssr: false })
const VisionSandboxPanel = dynamic(() => import('./VisionSandboxPanel'), { ssr: false })
const WorkTimeline   = dynamic(() => import('./WorkTimeline'), { ssr: false })
const ActivityFeed   = dynamic(() => import('./ActivityFeed'), { ssr: false })
const MissionChecklist = dynamic(() => import('./MissionChecklist'), { ssr: false })
const VoicePanel       = dynamic(() => import('./VoicePanel'),       { ssr: false })

const NAV_KEYS: Record<string, Tab> = {
  'g': 'HOME', '1': 'CHAT', '2': 'SYSTEM', '3': 'PLUGINS', '4': 'SKILL',
  '5': 'AGENT', '6': 'TIMELINE', '7': 'MEMORY', '8': 'DASHBOARD',
  '9': 'SETTINGS', '0': 'WORKFLOW', 'm': 'MISSIONS', 'v': 'VISION',
  'w': 'WORK', 'f': 'FEED', 'c': 'CHECKLIST', 'h': 'VOICE',
}

function useTheme() {
  const [theme, setTheme] = useState<string>('dark')
  useEffect(() => {
    const saved = localStorage.getItem('ev-theme') ?? 'dark'
    setTheme(saved)
    document.documentElement.setAttribute('data-theme', saved)
  }, [])
  const toggle = useCallback(() => {
    setTheme(t => {
      const next = t === 'dark' ? 'light' : 'dark'
      document.documentElement.setAttribute('data-theme', next)
      localStorage.setItem('ev-theme', next)
      return next
    })
  }, [])
  return [theme, toggle] as const
}

export default function EVApp() {
  const connect        = useEV(s => s.connect)
  const connectMetrics = useEV(s => s.connectMetrics)
  const connectChat    = useEV(s => s.connectChat)
  const connectConfirm = useEV(s => s.connectConfirm)
  const fetchPlugins   = useEV(s => s.fetchPlugins)
  const fetchAgents    = useEV(s => s.fetchAgents)
  const connError      = useEV(s => s.connError)
  const clearMessages  = useEV(s => s.clearMessages)
  const addMessage     = useEV(s => s.addMessage)
  const addToast       = useEV(s => s.addToast)
  const retry          = useEV(s => s.retry)
  const fetchDuplexFlag = useEV(s => s.fetchDuplexFlag)
  const startMic       = useEV(s => s.startMic)
  const setOrbState    = useEV(s => s.setOrbState)
  const [tab, setTab]  = useState<Tab>('HOME')
  const [chatOpen, setChatOpen] = useState(false)
  const [briefing, setBriefing] = useState('')
  const [needsTap, setNeedsTap] = useState(true)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [spotlightOpen, setSpotlightOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [theme, toggleTheme] = useTheme()

  useEffect(() => {
    connect(); connectMetrics(); connectChat(); connectConfirm()
    fetchPlugins(); fetchAgents()
    fetchDuplexFlag()
  }, [connect, connectMetrics, connectChat, connectConfirm, fetchPlugins, fetchAgents, fetchDuplexFlag])

  useEffect(() => {
    if (helloBooted) {
      setNeedsTap(false)
      void startMic()
      return
    }
    let cancelled = false
    let started = false
    let pendingTap = false
    let hello = 'Čau. Jsem tady.'
    let prepared: HTMLAudioElement | null = null

    const finishBoot = async () => {
      helloBooted = true
      if (cancelled) return
      addMessage(hello, 'ev')
      try {
        const br = await fetch(apiUrl('/api/voice/briefing'))
        const bd = await br.json()
        if (!cancelled && bd?.text) {
          setBriefing(`${hello} ${bd.text}`)
          setOrbState('speaking')
          await playReplySpeech(bd.text)
        }
      } catch { /* briefing optional */ }
      if (cancelled) return
      await startMic()
      setOrbState('listening')
    }

    const playHelloNow = async () => {
      if (started || cancelled || !prepared) return
      started = true
      unlockAudio()
      setNeedsTap(false)
      setOrbState('speaking')
      const ok = await playPreparedSpeech(prepared)
      if (!ok) {
        started = false
        setNeedsTap(true)
        setOrbState('idle')
        return
      }
      helloBooted = true
      prepared = null
      window.removeEventListener('pointerdown', onTap)
      await finishBoot()
    }

    const onTap = () => {
      pendingTap = true
      unlockAudio()
      void playHelloNow()
    }

    ;(async () => {
      try {
        const r = await fetch(apiUrl('/api/voice/greeting'))
        const d = await r.json()
        if (cancelled) return
        hello = (d.hello || d.text || hello).trim()
        setBriefing(hello)
        prepared = await prepareReplySpeech(hello)
        if (cancelled || !prepared) {
          setNeedsTap(true)
          return
        }
        if (pendingTap) {
          await playHelloNow()
          return
        }
        started = true
        const ok = await playPreparedSpeech(prepared).catch(() => false)
        if (cancelled) return
        if (ok) {
          helloBooted = true
          prepared = null
          setNeedsTap(false)
          setOrbState('speaking')
          window.removeEventListener('pointerdown', onTap)
          await finishBoot()
          return
        }
        started = false
        if (pendingTap) {
          await playHelloNow()
        } else {
          setNeedsTap(true)
        }
      } catch {
        setNeedsTap(true)
      }
    })()

    window.addEventListener('pointerdown', onTap)
    return () => {
      cancelled = true
      window.removeEventListener('pointerdown', onTap)
    }
  }, [addMessage, startMic, setOrbState])

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); setPaletteOpen(p => !p) }
      // Alt+Space → Spotlight (kdekoliv v OS přes web)
      if (e.altKey && e.code === 'Space') { e.preventDefault(); setSpotlightOpen(p => !p) }
      if (e.key === 'Escape') {
        setPaletteOpen(false)
        setSpotlightOpen(false)
        setChatOpen(false)
      }
      if (e.altKey && !e.ctrlKey && NAV_KEYS[e.key]) { e.preventDefault(); setTab(NAV_KEYS[e.key]) }
      if (e.altKey && e.key === 'd') {
        e.preventDefault()
        fetch(`${process.env.NODE_ENV === 'production' ? '' : 'http://127.0.0.1:8002'}/api/activity/report?format=md`)
          .then(r => r.json())
          .then(d => {
            addMessage(d.markdown || d.summary_text || 'Žádná aktivita.', 'ev')
            addToast('Denní shrnutí (Alt+D)', 'success', 3000)
          })
          .catch(() => addToast('Shrnutí dne selhalo', 'error', 3000))
      }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [addMessage, addToast])

  const PageWrapper = ({ children }: { children: React.ReactNode }) => (
    <div className="flex-1 overflow-y-auto flex flex-col items-center p-3 gap-3">
      <div className="w-full max-w-[860px] flex flex-col gap-3">{children}</div>
    </div>
  )

  return (
    <ErrorBoundary>
      <div data-testid="ev-app" className="flex h-screen overflow-hidden relative z-10">
        {/* Mobile backdrop */}
        {sidebarOpen && (
          <div
            className="md:hidden fixed inset-0 z-40 bg-black/50"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <Sidebar
          tab={tab} setTab={(t) => { setTab(t); if (t !== 'HOME') setChatOpen(false) }}
          setPaletteOpen={setPaletteOpen}
          setSpotlightOpen={setSpotlightOpen}
          clearMessages={clearMessages}
          onOpenChat={() => { setTab('HOME'); setChatOpen(true) }}
          theme={theme} toggleTheme={toggleTheme}
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
        />

        <div className="flex-1 flex flex-col overflow-hidden main-content-full">
          {/* Mobile hamburger */}
          <button
            className="md:hidden fixed top-3 left-3 z-50 p-2 rounded-lg"
            style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
            onClick={() => setSidebarOpen(true)}
            aria-label="Open menu"
          >
            ☰
          </button>

          {/* Status Bar — not on cinematic home */}
          {tab !== 'HOME' && (
            <div className="shrink-0 px-4 pt-3 pb-0 pl-14 md:pl-4">
              <EVStatusBar />
            </div>
          )}

          {/* Error banner */}
          {connError && (
            <div className="flex items-center gap-3 px-5 py-2.5 shrink-0 text-sm mx-4 mt-2 rounded-xl"
              style={{ background: 'rgba(248,113,113,.08)', border: '1px solid rgba(248,113,113,.2)' }}>
              <span className="flex-1" style={{ color: 'var(--red)' }}>{connError}</span>
              <button onClick={retry} className="btn-ghost px-3 py-1 text-xs" style={{ color: 'var(--red)' }}>
                Zkusit znovu
              </button>
            </div>
          )}

          {/* Pages */}
          <div className="flex-1 overflow-hidden flex relative">
            {tab === 'HOME' && (
              <>
                <ErrorBoundary>
                  <HomePanel
                    onOpenChat={() => setChatOpen(true)}
                    dimmed={chatOpen}
                    briefing={briefing}
                    needsTap={needsTap}
                    onStartVoice={() => unlockAudio()}
                  />
                </ErrorBoundary>
                {chatOpen && (
                  <div className="home-chat-sheet" data-testid="home-chat-sheet">
                    <ErrorBoundary>
                      <ChatPanel onClose={() => setChatOpen(false)} />
                    </ErrorBoundary>
                  </div>
                )}
              </>
            )}
            {tab === 'CHAT' && (
              <>
                <ErrorBoundary><ChatPanel /></ErrorBoundary>
                <ErrorBoundary><ContextSidebar /></ErrorBoundary>
              </>
            )}
            {tab === 'SYSTEM' && (
              <div className="flex flex-col overflow-hidden p-3 gap-3 w-full max-w-md">
                <ErrorBoundary><SystemPanel fullMode /></ErrorBoundary>
              </div>
            )}
            {tab === 'PLUGINS' && (
              <PageWrapper>
                <div className="card p-5"><ErrorBoundary><PluginMarketplace /></ErrorBoundary></div>
              </PageWrapper>
            )}
            {tab === 'WORK' && (
              <PageWrapper><ErrorBoundary><WorkTimeline /></ErrorBoundary></PageWrapper>
            )}
            {tab === 'FEED' && (
              <PageWrapper><ErrorBoundary><ActivityFeed /></ErrorBoundary></PageWrapper>
            )}
            {tab === 'CHECKLIST' && (
              <PageWrapper><ErrorBoundary><MissionChecklist /></ErrorBoundary></PageWrapper>
            )}
            {tab === 'AGENT' && (
              <PageWrapper>
                <div className="card p-0 overflow-hidden">
                  <ErrorBoundary><AgentGraphV2 active={tab === 'AGENT'} /></ErrorBoundary>
                </div>
              </PageWrapper>
            )}
            {tab === 'MISSIONS' && (
              <PageWrapper><ErrorBoundary><MissionPanel /></ErrorBoundary></PageWrapper>
            )}
            {tab === 'VISION' && (
              <PageWrapper><ErrorBoundary><VisionSandboxPanel /></ErrorBoundary></PageWrapper>
            )}
            {tab === 'VOICE' && (
              <PageWrapper>
                <ErrorBoundary><VoicePanel /></ErrorBoundary>
              </PageWrapper>
            )}
            {tab === 'WORKFLOW' && (
              <PageWrapper>
                <div className="card p-0 overflow-hidden">
                  <ErrorBoundary><WorkflowEditor /></ErrorBoundary>
                </div>
              </PageWrapper>
            )}
            {tab === 'TIMELINE' && (
              <PageWrapper><ErrorBoundary><AgentTimeline /></ErrorBoundary></PageWrapper>
            )}
            {tab === 'MEMORY' && (
              <PageWrapper><ErrorBoundary><MemoryGraph /></ErrorBoundary></PageWrapper>
            )}
            {tab === 'SKILL' && (
              <PageWrapper><ErrorBoundary><SkillGenerator /></ErrorBoundary></PageWrapper>
            )}
            {tab === 'DASHBOARD' && (
              <div className="flex-1 overflow-y-auto p-3">
                <div className="max-w-[1100px] mx-auto">
                  <ErrorBoundary><DashboardPanel /></ErrorBoundary>
                </div>
              </div>
            )}
            {tab === 'SETTINGS' && (
              <div className="page-wrap-center">
                <ErrorBoundary><SettingsPanel /></ErrorBoundary>
              </div>
            )}
          </div>
        </div>

        <ToastContainer />
        <ConfirmModal />
        <OnboardingWizard />
      <Spotlight
        open={spotlightOpen}
        onClose={() => setSpotlightOpen(false)}
        onCommand={() => { setTab('HOME'); setChatOpen(true); setSpotlightOpen(false) }}
      />
        {paletteOpen && (
          <div className="fixed inset-0 z-50 flex items-start justify-center pt-24"
            style={{ background: 'rgba(10,11,16,.8)', backdropFilter: 'blur(12px)' }}
            onClick={() => setPaletteOpen(false)}>
            <div className="w-[480px] rounded-2xl overflow-hidden anim-slide-up glass-panel"
              style={{ boxShadow: '0 24px 64px rgba(0,0,0,.5)' }}
              onClick={e => e.stopPropagation()}>
              <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
                <div className="font-display text-sm font-semibold">Paleta příkazů</div>
                <div className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>Alt+1–9, Alt+W/F/C/M (Dnes/Feed/Release/Mise)</div>
              </div>
              <div className="p-2">
                {Object.entries(NAV_KEYS).map(([key, id]) => (
                  <button key={id}
                    onClick={() => { setTab(id); setPaletteOpen(false) }}
                    className="nav-item">
                    <kbd className="font-mono text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'rgba(255,255,255,.05)', border: '1px solid var(--border)' }}>
                      Alt+{key}
                    </kbd>
                    {id}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </ErrorBoundary>
  )
}
