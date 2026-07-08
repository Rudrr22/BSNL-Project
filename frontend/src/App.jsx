import { Suspense, lazy, useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Activity, Bot, ClipboardList, Globe, LayoutDashboard, Loader2, Map, RadioTower, Search, ShieldCheck, TrendingUp, UploadCloud, Wifi } from 'lucide-react'
import { getApiBaseUrl } from './utils/api'

// 🚀 Code Splitting: Lazy load pages to optimize initial bundle size
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Upload = lazy(() => import('./pages/Upload'))
const Chat = lazy(() => import('./pages/Chat'))
const History = lazy(() => import('./pages/History'))
const Topology = lazy(() => import('./pages/Topology'))
const Coverage = lazy(() => import('./pages/Coverage'))
const Explorer = lazy(() => import('./pages/Explorer'))
const KPIs = lazy(() => import('./pages/KPIs'))

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/kpis', icon: TrendingUp, label: 'KPI Analytics' },
  { path: '/topology', icon: Globe, label: 'Topology' },
  { path: '/coverage', icon: Map, label: 'Coverage' },
  { path: '/upload', icon: UploadCloud, label: 'Upload Logs' },
  { path: '/chat', icon: Bot, label: 'AI Chat' },
  { path: '/explorer', icon: Search, label: 'NL → SQL' },
  { path: '/history', icon: ClipboardList, label: 'History' },
]

function Sidebar() {
  const [backendOnline, setBackendOnline] = useState(false)

  useEffect(() => {
    let active = true
    async function checkBackend() {
      try {
        const response = await fetch(getApiBaseUrl() + '/health')
        if (active) setBackendOnline(response.ok)
      } catch (error) {
        if (active) setBackendOnline(false)
      }
    }
    checkBackend()
    const timer = window.setInterval(checkBackend, 15000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [])

  return (
    <aside className="sidebar">
      <div className="brand-block">
        <div className="brand-mark" aria-hidden="true">
          <img src="/favicon.svg" alt="BSNL Logo" style={{ height: '36px', width: 'auto', objectFit: 'contain' }} />
        </div>
        <div><h1>Teleguard</h1><p>BSNL Network Monitor</p></div>
      </div>

      <nav className="nav-list" aria-label="Primary navigation">
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <NavLink key={item.path} to={item.path} end={item.path === '/'} className="nav-link">
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </nav>

      <div className="sidebar-status">
        <div className={backendOnline ? 'status-row online' : 'status-row offline'}><Activity size={14} /><span>{backendOnline ? 'Backend Online' : 'Backend Offline'}</span></div>
        <div className="mini-grid">
          <span><RadioTower size={14} /> Live feed</span>
          <span><Wifi size={14} /> RAG ready</span>
        </div>
        <strong>Teleguard v2.0</strong>
      </div>
    </aside>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="app-shell">
          <Sidebar />
          <main className="main-panel">
            <Suspense fallback={
              <div style={{ display: 'grid', placeItems: 'center', height: '60vh', color: 'var(--muted)' }}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                  <Loader2 size={32} className="spin" style={{ color: 'var(--blue)' }} />
                  <span style={{ fontSize: '13px', fontWeight: 600, letterSpacing: '0.05em' }}>LOADING MODULE...</span>
                </div>
              </div>
            }>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/kpis" element={<KPIs />} />
                <Route path="/topology" element={<Topology />} />
                <Route path="/coverage" element={<Coverage />} />
                <Route path="/upload" element={<Upload />} />
                <Route path="/chat" element={<Chat />} />
                <Route path="/explorer" element={<Explorer />} />
                <Route path="/history" element={<History />} />
              </Routes>
            </Suspense>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
