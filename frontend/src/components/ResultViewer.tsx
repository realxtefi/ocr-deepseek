import { useEffect, useState } from 'react'
import { getJobResult } from '../api'

interface Props {
  jobId: string
}

interface FileResult {
  file_path: string
  content?: string
  error?: string
}

export default function ResultViewer({ jobId }: Props) {
  const [results, setResults] = useState<FileResult[]>([])
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [tab, setTab] = useState<'formatted' | 'raw'>('formatted')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const data = await getJobResult(jobId)
        setResults(data.results || [])
      } catch {
        setResults([])
      }
      setLoading(false)
    }
    load()
  }, [jobId])

  if (loading) return <div className="card"><p>Loading results...</p></div>
  if (results.length === 0) return <div className="card"><p>No results yet.</p></div>

  const current = results[selectedIdx]

  const copyToClipboard = () => {
    if (current?.content) {
      navigator.clipboard.writeText(current.content)
    }
  }

  const downloadResult = () => {
    if (!current?.content) return
    const blob = new Blob([current.content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const name = current.file_path.split(/[\\/]/).pop() || 'result'
    a.href = url
    a.download = `${name}_result.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  // Try to parse JSON for structured view
  let structured: Record<string, unknown> | null = null
  if (current?.content) {
    try {
      structured = JSON.parse(current.content)
    } catch { /* not JSON */ }
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h2>Results</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-secondary" onClick={copyToClipboard} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
            Copy
          </button>
          <button className="btn btn-secondary" onClick={downloadResult} style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
            Download
          </button>
        </div>
      </div>

      {results.length > 1 && (
        <div className="form-row" style={{ marginBottom: 12 }}>
          <select
            value={selectedIdx}
            onChange={e => setSelectedIdx(parseInt(e.target.value))}
          >
            {results.map((r, i) => (
              <option key={i} value={i}>
                {r.file_path.split(/[\\/]/).pop()}
              </option>
            ))}
          </select>
        </div>
      )}

      {current?.error && (
        <div style={{ padding: 12, background: 'rgba(239,68,68,0.1)', borderRadius: 8, color: 'var(--error)', marginBottom: 12 }}>
          Error: {current.error}
        </div>
      )}

      {current?.content && (
        <>
          {structured && (
            <div className="result-tabs">
              <button className={tab === 'formatted' ? 'active' : ''} onClick={() => setTab('formatted')}>
                Structured
              </button>
              <button className={tab === 'raw' ? 'active' : ''} onClick={() => setTab('raw')}>
                Raw
              </button>
            </div>
          )}

          {tab === 'formatted' && structured ? (
            <div className="result-content">
              <StructuredView data={structured} />
            </div>
          ) : (
            <div className="result-content">
              {current.content}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function StructuredView({ data }: { data: Record<string, unknown> }) {
  const meta = data.metadata as Record<string, unknown> | undefined

  if (!meta) {
    return <pre>{JSON.stringify(data, null, 2)}</pre>
  }

  return (
    <div style={{ fontFamily: 'inherit' }}>
      {meta.title && <div style={{ marginBottom: 8 }}><strong>Title:</strong> {String(meta.title)}</div>}
      {Array.isArray(meta.authors) && meta.authors.length > 0 && (
        <div style={{ marginBottom: 8 }}><strong>Authors:</strong> {meta.authors.join(', ')}</div>
      )}
      {meta.journal_or_series && (
        <div style={{ marginBottom: 8 }}><strong>Journal:</strong> {String(meta.journal_or_series)}</div>
      )}
      {meta.doi && <div style={{ marginBottom: 8 }}><strong>DOI:</strong> {String(meta.doi)}</div>}
      {meta.abstract && (
        <div style={{ marginBottom: 8 }}>
          <strong>Abstract:</strong>
          <div style={{ marginTop: 4, paddingLeft: 8, borderLeft: '2px solid var(--border)' }}>
            {String(meta.abstract)}
          </div>
        </div>
      )}
      {Array.isArray(meta.figures) && meta.figures.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <strong>Figures:</strong>
          {(meta.figures as Array<{ number: number; caption: string }>).map(fig => (
            <div key={fig.number} style={{ marginTop: 4, paddingLeft: 8 }}>
              <em>Figure {fig.number}:</em> {fig.caption}
            </div>
          ))}
        </div>
      )}
      {meta.extraction_confidence && (
        <div style={{ marginTop: 12, fontSize: '0.8rem', color: 'var(--text-dim)' }}>
          <strong>Confidence:</strong>{' '}
          {Object.entries(meta.extraction_confidence as Record<string, number>)
            .map(([k, v]) => `${k}: ${Math.round(v * 100)}%`)
            .join(' | ')}
        </div>
      )}
    </div>
  )
}
