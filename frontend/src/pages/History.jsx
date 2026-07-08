import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CalendarClock, CheckCircle2, Clock3, Download, FileSearch, Search, XCircle, Loader2 } from 'lucide-react'
import AnomalyCard from '../components/AnomalyCard'
import { endpoints } from '../utils/api'

function statusIcon(status) {
  if (status === 'complete') return <CheckCircle2 size={15} />
  if (status === 'failed') return <XCircle size={15} />
  return <Clock3 size={15} />
}

export default function History() {
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [downloading, setDownloading] = useState(null) // Stores the ID of the report being downloaded

  const { data: analyses = [], isLoading } = useQuery({ 
    queryKey: ['analyses'], 
    queryFn: () => endpoints.analyses().then((r) => r.data), 
    refetchInterval: 20000 
  })

  const filtered = useMemo(() => {
    const term = search.toLowerCase()
    return analyses.filter((item) => [item.filename, item.status, item.source, item.summary].filter(Boolean).join(' ').toLowerCase().includes(term))
  }, [analyses, search])

  const selected = filtered.find((item) => item.id === selectedId) || filtered[0]

  const handleDownloadPDF = async (id, filename) => {
    try {
      setDownloading(id)

      const { getApiBaseUrl } = await import('../utils/api')
      const response = await fetch(`${getApiBaseUrl()}/api/analyses/${id}/pdf`)

      if (!response.ok) throw new Error(`Server returned ${response.status}`)

      const arrayBuffer = await response.arrayBuffer()
      if (arrayBuffer.byteLength === 0) throw new Error('Received empty file from server')

      const blob = new Blob([arrayBuffer], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)

      const nameBase = filename ? filename.replace(/\.[^/.]+$/, '') : `Session_${id}`
      const link = document.createElement('a')
      link.href = url
      link.download = `TeleGuard_Report_${nameBase}.pdf`  // ← property, not setAttribute
      link.style.display = 'none'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      // Revoke after 10 s — Chrome must finish writing the file first
      setTimeout(() => URL.revokeObjectURL(url), 10000)

    } catch (error) {
      console.error('PDF download failed:', error)
      alert(`Could not download PDF: ${error.message}`)
    } finally {
      setDownloading(null)
    }
  }


  return (
    <div className="page fade-in">
      <header className="page-header compact-header">
        <span className="eyebrow">Audit trail</span>
        <h1>Analysis history</h1>
        <p>Review uploaded log sessions, AI summaries, severity counts, and detected anomalies.</p>
      </header>

      <section className="history-layout">
        <div className="panel history-list-panel">
          <div className="search-box"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search filename, status, summary..." /></div>
          <div className="history-list">
            {isLoading ? <div className="empty-state">Loading analysis sessions...</div> : null}
            {!isLoading && !filtered.length ? <div className="empty-state">No analysis history yet.</div> : null}
            {filtered.map((item) => (
              <button className={selected?.id === item.id ? 'history-item active' : 'history-item'} type="button" key={item.id} onClick={() => setSelectedId(item.id)}>
                <span className={'status-chip ' + item.status}>{statusIcon(item.status)} {item.status}</span>
                <strong>{item.filename || 'Live analysis #' + item.id}</strong>
                <small><CalendarClock size={13} /> {new Date(item.created_at).toLocaleString()}</small>
                <div className="counts"><span>{item.total_logs} logs</span><span>{item.critical_count} critical</span><span>{item.warning_count} warnings</span></div>
              </button>
            ))}
          </div>
        </div>

        <div className="panel history-detail-panel">
          {selected ? (
            <>
              <div className="section-heading"><div><span className="eyebrow">Session #{selected.id}</span><h2>{selected.filename || 'Live analysis'}</h2></div><FileSearch size={22} /></div>
              <div className="result-grid compact">
                <span><strong>{selected.total_logs}</strong>Total logs</span>
                <span><strong>{selected.critical_count}</strong>Critical</span>
                <span><strong>{selected.warning_count}</strong>Warning</span>
                <span><strong>{selected.info_count}</strong>Info</span>
              </div>
              <div className="detail-block"><h3>AI summary</h3><p>{selected.summary || 'Summary will appear when background analysis completes.'}</p></div>
              <div className="detail-block"><h3>Recommendations</h3><p>{selected.recommendations || 'Recommendations are not available yet.'}</p></div>
              {selected.status === 'complete' && (
                <div className="detail-block">
                  <button
                    onClick={() => handleDownloadPDF(selected.id, selected.filename)}
                    className="primary-button"
                    disabled={downloading === selected.id}
                    style={{ gap: '8px', cursor: 'pointer' }}
                  >
                    {downloading === selected.id ? (
                      <>
                        <Loader2 className="spin" size={16} /> Generating PDF...
                      </>
                    ) : (
                      <>
                        <Download size={16} /> Download PDF Report
                      </>
                    )}
                  </button>
                </div>
              )}
              <div className="detail-block"><h3>Anomalies</h3><div className="anomaly-stack">{selected.anomalies?.length ? selected.anomalies.map((anomaly) => <AnomalyCard key={anomaly.id} anomaly={anomaly} compact />) : <div className="empty-state">No anomalies linked to this session.</div>}</div></div>
            </>
          ) : <div className="empty-state">Select an analysis session to inspect details.</div>}
        </div>
      </section>
    </div>
  )
}
