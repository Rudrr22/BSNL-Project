import { useMemo, useRef, useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { FileCheck2, FileText, Loader2, UploadCloud, CheckCircle2 } from 'lucide-react'
import { endpoints } from '../utils/api'

export default function Upload() {
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [isPolling, setIsPolling] = useState(false)

  const upload = useMutation({ 
    mutationFn: endpoints.uploadLogs,
    onSuccess: (res) => {
      setAnalysisResult(res.data)
      if (res.data.status === 'processing') {
        setIsPolling(true)
      }
    }
  })

  // Poll for background AI analysis completion
  useEffect(() => {
    let timer;
    if (isPolling && analysisResult) {
      const id = analysisResult.analysis_id || analysisResult.id;
      timer = setInterval(async () => {
        try {
          const res = await endpoints.analysis(id);
          setAnalysisResult(res.data);
          if (res.data.status === 'complete' || res.data.status === 'failed') {
            setIsPolling(false);
          }
        } catch (err) {
          setIsPolling(false);
        }
      }, 3000);
    }
    return () => clearInterval(timer);
  }, [isPolling, analysisResult]);

  const preview = useMemo(() => {
    if (!file) return null
    return { name: file.name, size: (file.size / 1024).toFixed(1) + ' KB', type: file.type || 'log/text file' }
  }, [file])

  function pickFile(selected) {
    const nextFile = selected?.[0]
    if (nextFile) {
      setFile(nextFile)
      upload.reset()
      setAnalysisResult(null)
      setIsPolling(false)
    }
  }

  function submit() {
    if (file) upload.mutate(file)
  }

  return (
    <div className="page fade-in">
      <header className="page-header">
        <span className="eyebrow">Batch analysis</span>
        <h1>Upload telecom logs</h1>
        <p>Send captured network logs to the backend pipeline for multi-agent analysis, anomaly extraction, and RAG indexing.</p>
      </header>

      <section className="upload-layout">
        <div className="panel upload-panel">
          <div
            className={dragging ? 'drop-zone dragging' : 'drop-zone'}
            onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); pickFile(event.dataTransfer.files) }}
            onClick={() => inputRef.current?.click()}
            role="button"
            tabIndex={0}
          >
            <input ref={inputRef} type="file" accept=".log,.txt,.csv" onChange={(event) => pickFile(event.target.files)} hidden />
            <div className="drop-icon"><UploadCloud size={38} /></div>
            <h2>{preview ? preview.name : 'Drop log file here'}</h2>
            <p>{preview ? preview.size + ' • ' + preview.type : 'Choose .log, .txt, or .csv files from simulator or field captures.'}</p>
          </div>

          <div className="upload-actions">
            <button className="primary-button" type="button" disabled={!file || upload.isLoading || upload.isPending} onClick={submit}>
              {(upload.isLoading || upload.isPending) ? <Loader2 size={18} className="spin" /> : <FileCheck2 size={18} />}
              {(upload.isLoading || upload.isPending) ? 'Uploading...' : 'Start AI Analysis'}
            </button>
            <button className="ghost-button" type="button" onClick={() => { setFile(null); upload.reset(); setAnalysisResult(null); setIsPolling(false); }}>Clear</button>
          </div>

          {analysisResult ? (
            <div className="detail-block fade-in" style={{ marginTop: '24px' }}>
              <div className="section-heading">
                <div>
                  <span className="eyebrow">Submitted</span>
                  <h3>Analysis #{analysisResult.analysis_id || analysisResult.id}</h3>
                </div>
                {isPolling ? <Loader2 size={18} className="spin tone-blue" /> : <CheckCircle2 size={18} className="tone-green" />}
              </div>
              
              <div className="result-grid" style={{ marginBottom: '16px' }}>
                <span><strong>{analysisResult.total_logs}</strong>Total</span>
                <span><strong className="tone-red">{analysisResult.critical_count ?? analysisResult.critical}</strong>Critical</span>
                <span><strong className="tone-amber">{analysisResult.warning_count ?? analysisResult.warning}</strong>Warnings</span>
                <span><strong className="tone-green">{analysisResult.info_count ?? analysisResult.info}</strong>Info</span>
              </div>
              
              <p style={{ display: 'flex', alignItems: 'center', gap: '8px', color: isPolling ? 'var(--blue)' : 'var(--green)' }}>
                {isPolling ? (
                  <>
                    <Loader2 size={14} className="spin" />
                    AI agents are currently analyzing your logs in the background...
                  </>
                ) : (
                  '✅ Analysis Complete'
                )}
              </p>

              {analysisResult.summary && (
                <div className="fade-in" style={{ marginTop: '16px', padding: '16px', background: 'var(--panel-2)', borderRadius: '10px', border: '1px solid var(--line)' }}>
                  <h4 style={{ color: 'var(--blue)', marginBottom: '8px', fontSize: '15px' }}>AI Executive Summary</h4>
                  <p style={{ fontSize: '14px', color: 'var(--text)', whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>{analysisResult.summary}</p>
                </div>
              )}
              {analysisResult.recommendations && (
                <div className="fade-in" style={{ marginTop: '12px', padding: '16px', background: 'var(--panel-2)', borderRadius: '10px', border: '1px solid var(--line)' }}>
                  <h4 style={{ color: 'var(--amber)', marginBottom: '8px', fontSize: '15px' }}>Actionable Recommendations</h4>
                  <p style={{ fontSize: '14px', color: 'var(--text)', whiteSpace: 'pre-wrap', lineHeight: '1.6' }}>{analysisResult.recommendations}</p>
                </div>
              )}
            </div>
          ) : null}
        </div>

        <aside className="panel process-panel">
          <span className="eyebrow">Pipeline</span>
          <h2>What happens next</h2>
          <div className="steps">
            <span><FileText size={17} /> Parse raw lines and severity counts</span>
            <span><FileText size={17} /> Store analysis session in PostgreSQL</span>
            <span><FileText size={17} /> Run AI anomaly workflow in background</span>
            <span><FileText size={17} /> Index logs for chat answers</span>
          </div>
        </aside>
      </section>

      {upload.isError ? <div className="error-banner" style={{ marginTop: '24px' }}>Upload failed. Check that the backend is running and the file is readable.</div> : null}
    </div>
  )
}
