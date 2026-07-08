import { useState, useEffect, useRef } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Clock, Code2, Download, Loader2, Play, Search, Table2, Terminal, X } from 'lucide-react'
import { api } from '../utils/api'

const HISTORY_KEY = 'teleguard_query_history'
const MAX_HISTORY = 8

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') } catch { return [] }
}
function saveToHistory(q) {
  const updated = [q, ...loadHistory().filter(x => x !== q)].slice(0, MAX_HISTORY)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
}

function exportResultsAsCSV(columns, results) {
  const header = columns.join(',')
  const rows = results.map(row =>
    columns.map(col => {
      const val = row[col]
      if (val === null || val === undefined) return ''
      const str = String(val)
      return str.includes(',') || str.includes('\n') || str.includes('"')
        ? `"${str.replace(/"/g, '""')}"` : str
    }).join(',')
  )
  const csv = '\uFEFF' + [header, ...rows].join('\n')   // BOM for Excel UTF-8
  const filename = `teleguard_query_${Date.now()}.csv`

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename          // ← property assignment, not setAttribute
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  // Revoke after 10 s — Chrome must finish writing the file before revocation
  setTimeout(() => URL.revokeObjectURL(url), 10000)
}

export default function Explorer() {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState(loadHistory)
  const [showHistory, setShowHistory] = useState(false)
  const inputRef = useRef(null)

  const query = useMutation({
    mutationFn: (q) => api.post('/api/nl2sql', { question: q }).then(r => r.data),
    onSuccess: (_, q) => { saveToHistory(q); setHistory(loadHistory()) }
  })

  function run(text = question) {
    const q = text.trim()
    if (!q || query.isPending) return
    setQuestion(q)
    setShowHistory(false)
    query.mutate(q)
  }

  function clearHistory() { localStorage.removeItem(HISTORY_KEY); setHistory([]) }

  // Close history dropdown on outside click
  useEffect(() => {
    const handler = (e) => { if (!inputRef.current?.contains(e.target)) setShowHistory(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const result = query.data

  return (
    <div className="page fade-in">
      <header className="page-header compact-header">
        <span className="eyebrow">AI-powered data explorer</span>
        <h1>Natural Language Query</h1>
        <p>Ask questions in plain English — the AI writes and executes SQL on your live database.</p>
      </header>

      <section className="explorer-layout">
        <div className="panel explorer-main">

          {/* ── Input with inline history dropdown ── */}
          <div style={{ position: 'relative' }} ref={inputRef}>
            <div className="chat-input" style={{ gridTemplateColumns: '1fr 48px' }}>
              <input
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onFocus={() => history.length > 0 && setShowHistory(true)}
                onKeyDown={e => {
                  if (e.key === 'Enter') run()
                  if (e.key === 'Escape') setShowHistory(false)
                }}
                placeholder="Type a question to execute a natural language SQL query..."
              />
              <button
                className="primary-button icon-button"
                onClick={() => run()}
                disabled={query.isPending || !question.trim()}
                aria-label="Run query"
              >
                {query.isPending ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
              </button>
            </div>

            {/* Subtle history dropdown — appears under input on focus */}
            {showHistory && history.length > 0 && (
              <div style={{
                position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
                background: 'var(--surface)', border: '1px solid var(--border)',
                borderRadius: '10px', marginTop: '4px', overflow: 'hidden',
                boxShadow: '0 8px 24px rgba(0,0,0,0.4)'
              }}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '8px 12px', borderBottom: '1px solid var(--border)',
                  color: 'var(--muted)', fontSize: '11px'
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <Clock size={11} /> Recent
                  </span>
                  <button
                    onClick={(e) => { e.stopPropagation(); clearHistory(); setShowHistory(false) }}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: '3px', fontSize: '11px', padding: '2px 4px' }}
                  >
                    <X size={10} /> Clear
                  </button>
                </div>
                {history.map((q, i) => (
                  <button
                    key={i}
                    onMouseDown={() => run(q)}
                    style={{
                      width: '100%', textAlign: 'left', padding: '9px 14px',
                      background: 'none', border: 'none', cursor: 'pointer',
                      color: 'var(--text)', fontSize: '13px',
                      borderBottom: i < history.length - 1 ? '1px solid var(--border)' : 'none',
                      display: 'flex', alignItems: 'center', gap: '8px',
                      transition: 'background 0.15s'
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-2)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'none'}
                  >
                    <Clock size={12} style={{ color: 'var(--muted)', flexShrink: 0 }} />
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{q}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* SQL Output */}
          {result?.sql && (
            <div className="sql-block">
              <div className="sql-header"><Code2 size={14} /> Generated SQL</div>
              <pre><code>{result.sql}</code></pre>
            </div>
          )}

          {/* Error */}
          {result?.error && (
            <div className="error-banner" style={{ marginTop: '14px' }}>{result.error}</div>
          )}

          {/* Results Table */}
          {result?.results?.length > 0 && (
            <div className="sql-results">
              <div className="sql-header" style={{ marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span><Table2 size={14} /> {result.row_count} rows returned</span>
                <button
                  className="ghost-button"
                  style={{ fontSize: '12px', padding: '4px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
                  onClick={() => exportResultsAsCSV(result.columns, result.results)}
                >
                  <Download size={13} /> Export CSV
                </button>
              </div>
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>{result.columns.map(col => <th key={col}>{col}</th>)}</tr>
                  </thead>
                  <tbody>
                    {result.results.map((row, i) => (
                      <tr key={i}>
                        {result.columns.map(col => (
                          <td key={col}>
                            {row[col] === null ? <span style={{ color: 'var(--muted)' }}>NULL</span> :
                              String(row[col]).length > 60 ? String(row[col]).slice(0, 60) + '...' : String(row[col])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>

      </section>
    </div>
  )
}
