'use client'
import { useEffect, useState, useCallback } from 'react'
import { useJarvis } from '@/store/jarvis'
import Sidebar, { type Tab } from './Sidebar'
import ChatPanel from './ChatPanel'
import ContextSidebar from './ContextSidebar'
import ToastContainer from './Toast'
import ErrorBoundary from './ErrorBoundary'
import Spotlight from './Spotlight'
import ConfirmModal from './ConfirmModal'
import OnboardingWizard from './OnboardingWizard'
import dynamic from 'next/dynamic'
import { JarvisStatusBar } from './HeroPanel'

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

const NAV_KEYS: Record<string, Tab> = {
  '1': 'CHAT', '2': 'SYSTEM', '3': 'PLUGINS', '4': 'SKILL',
  '5': 'AGENT', '6': 'TIMELINE', '7': 'MEMORY', '8': 'DASHBOARD',
  '9': 'SETTINGS', '0': 'WORKFLOW', 'm': 'MISSIONS', 'v': 'VISION',
  'w': 'WORK', 'f': 'FEED', 'c': 'CHECKLIST',
}

function useTheme() {
  const [theme, setTheme] = useState<string>('dark')
  useEffect(() => {
    const saved = localStorage.getItem('jarvis-theme') ?? 'dark'
    setTheme(saved)
    document.documentElement.setAttribute('data-theme', saved)
  }, [])
  const toggle = useCallback(() => {
    setTheme(t => {
      const next = t === 'dark' ? 'light' : 'dark'
      document.documentElement.setAttribute('data-theme', next)
      localStorage.setItem('jarvis-theme', next)
      return next
    })
  }, [])
  return [theme, toggle] as const
}

export default function JarvisApp() {
  const connect        = useJarvis(s => s.connect)
  const connectMetrics = useJarvis(s => s.connectMetrics)
  const connectChat    = useJarvis(s => s.connectChat)
  const connectConfirm = useJarvis(s => s.connectConfirm)
  const connError      = useJarvis(s => s.connError)
  const clearMessages  = useJarvis(s => s.clearMessages)
  const retry          = useJarvis(s => s.retry)
  const [tab, setTab]  = useState<Tab>('CHAT')
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [spotlightOpen, setSpotlightOpen] = useState(false)
  const [theme, toggleTheme] = useTheme()

  useEffect(() => {
    connect(); connectMetrics(); connectChat(); connectConfirm()
  }, [connect, connectMetrics, connectChat, connectConfirm])

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); setPaletteOpen(p => !p) }
      // Alt+Space → Spotlight (kdekoliv v OS přes web)
      if (e.altKey && e.code === 'Space') { e.preventDefault(); setSpotlightOpen(p => !p) }
      if (e.key === 'Escape') { setPaletteOpen(false); setSpotlightOpen(false) }
      if (e.altKey && !e.ctrlKey && NAV_KEYS[e.key]) { e.preventDefault(); setTab(NAV_KEYS[e.key]) }
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])

  const PageWrapper = ({ children }: { children: React.ReactNode }) => (
    <div className="flex-1 overflow-y-auto flex flex-col items-center p-3 gap-3">
      <div className="w-full max-w-[860px] flex flex-col gap-3">{children}</div>
    </div>
  )

  return (
    <ErrorBoundary>
      <div className="flex h-screen overflow-hidden relative z-10">
        <Sidebar
          tab={tab} setTab={setTab}
          setPaletteOpen={setPaletteOpen}
          setSpotlightOpen={setSpotlightOpen}
          clearMessages={clearMessages}
          theme={theme} toggleTheme={toggleTheme}
        />

        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Status Bar */}
          <div className="shrink-0 px-4 pt-3 pb-0">
            <JarvisStatusBar />
          </div>

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
          <div className="flex-1 overflow-hidden flex">
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
        onCommand={() => { setTab('CHAT'); setSpotlightOpen(false) }}
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
                <div className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>Alt+1–9, Alt+W/F/C (Dnes/Feed/Checklist)</div>
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
