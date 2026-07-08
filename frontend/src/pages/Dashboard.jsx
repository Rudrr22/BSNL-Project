import { useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, BarChart3, CheckCircle2, FileStack, RadioTower, ShieldAlert } from 'lucide-react'
import AnomalyCard from '../components/AnomalyCard'
import LogTicker from '../components/LogTicker'
import StatCard from '../components/StatCard'
import { endpoints } from '../utils/api'

const fallbackStats = { total_logs_today: 0, critical_count: 0, warning_count: 0, info_count: 0, most_affected_tower: 'Waiting for data', total_analyses: 0 }

export default function Dashboard() {
  const queryClient = useQueryClient()
  const { data: statsData, isLoading: statsLoading } = useQuery({ queryKey: ['stats'], queryFn: () => endpoints.stats().then((r) => r.data), refetchInterval: 15000 })
  const { data: logs = [] } = useQuery({ queryKey: ['recentLogs'], queryFn: () => endpoints.recentLogs(30).then((r) => r.data), refetchInterval: 12000 })
  const { data: anomalies = [] } = useQuery({ queryKey: ['anomalies'], queryFn: () => endpoints.anomalies({ limit: 6 }).then((r) => r.data), refetchInterval: 15000 })

  const acknowledge = useMutation({
    mutationFn: endpoints.acknowledge,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['anomalies'] }),
  })

  const stats = statsData || fallbackStats
  const severityData = [
    { name: 'Critical', value: stats.critical_count || 0, tone: 'critical' },
    { name: 'Warning', value: stats.warning_count || 0, tone: 'warning' },
    { name: 'Info', value: stats.info_count || 0, tone: 'info' },
  ]
  const maxSeverity = Math.max(...severityData.map((item) => item.value), 1)

  const pulseData = useMemo(() => {
    const base = logs.slice(0, 18).reverse()
    if (!base.length) return ['INFO', 'WARNING', 'INFO', 'CRITICAL', 'WARNING', 'INFO', 'CRITICAL', 'INFO']
    return base.map((log) => log.severity || 'INFO')
  }, [logs])

  return (
    <div className="page fade-in">
      <header className="hero-band">
        <div>
          <span className="eyebrow">AI assisted telecom operations</span>
          <h1>Network health command center</h1>
          <p>Monitor BSNL log activity, identify anomalous towers, and move faster from raw alarms to recommended actions.</p>
        </div>
        <div className="hero-metrics">
          <span>Most affected</span>
          <strong>{stats.most_affected_tower || 'No critical tower yet'}</strong>
          <small>{statsLoading ? 'Refreshing metrics' : 'Updated from backend stats'}</small>
        </div>
      </header>

      <section className="stats-grid">
        <StatCard icon={BarChart3} label="Total Logs" value={stats.total_logs_today} helper="All stored network events" tone="blue" trend="Live" />
        <StatCard icon={ShieldAlert} label="Critical" value={stats.critical_count} helper="Needs engineer attention" tone="red" />
        <StatCard icon={AlertTriangle} label="Warnings" value={stats.warning_count} helper="Degrading service signals" tone="amber" />
        <StatCard icon={FileStack} label="Analyses" value={stats.total_analyses} helper="AI review sessions" tone="green" />
      </section>

      <div className="dashboard-grid">
        <section className="panel chart-panel">
          <div className="section-heading"><div><span className="eyebrow">Severity mix</span><h2>Alarm Distribution</h2></div><CheckCircle2 size={18} /></div>
          <div className="bar-visual">
            {severityData.map((item) => (
              <div className="bar-line" key={item.name}>
                <div className="bar-label"><span>{item.name}</span><strong>{item.value}</strong></div>
                <div className="bar-track"><span className={'bar-fill ' + item.tone} style={{ width: Math.max(8, (item.value / maxSeverity) * 100) + '%' }} /></div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel chart-panel">
          <div className="section-heading"><div><span className="eyebrow">Recent movement</span><h2>Incident Pulse</h2></div><RadioTower size={18} /></div>
          <div className="pulse-visual">
            {pulseData.map((severity, index) => <span key={index} className={'pulse-bar ' + String(severity).toLowerCase()} style={{ height: 24 + ((index % 5) * 14) + 'px' }} />)}
          </div>
          <div className="pulse-legend"><span>Info</span><span>Warning</span><span>Critical</span></div>
        </section>
      </div>

      <div className="dashboard-grid lower">
        <section className="panel">
          <div className="section-heading"><div><span className="eyebrow">Open issues</span><h2>Priority Anomalies</h2></div></div>
          <div className="anomaly-stack">
            {anomalies.length ? anomalies.slice(0, 3).map((anomaly) => <AnomalyCard key={anomaly.id} anomaly={anomaly} onAcknowledge={(id) => acknowledge.mutate(id)} compact />) : <div className="empty-state">No anomalies detected yet.</div>}
          </div>
        </section>
        <LogTicker initialLogs={logs} />
      </div>
    </div>
  )
}
