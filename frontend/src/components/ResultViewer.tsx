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

type TabType = 'preview' | 'raw'

export default function ResultViewer({ jobId }: Props) {
  const [results, setResults] = useState<FileResult[]>([])
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [tab, setTab] = useState<TabType>('preview')
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

  // Detect content type
  let parsed: Record<string, unknown> | null = null
  let contentType: 'json' | 'markdown' | 'xml' | 'text' = 'text'
  if (current?.content) {
    const trimmed = current.content.trim()
    if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try {
        parsed = JSON.parse(trimmed)
        contentType = 'json'
      } catch { /* not JSON */ }
    } else if (trimmed.startsWith('<?xml') || trimmed.startsWith('<document')) {
      contentType = 'xml'
    } else if (trimmed.startsWith('#') || /^\*\*/.test(trimmed)) {
      contentType = 'markdown'
    }
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
          <div className="result-tabs">
            <button className={tab === 'preview' ? 'active' : ''} onClick={() => setTab('preview')}>
              Preview
            </button>
            <button className={tab === 'raw' ? 'active' : ''} onClick={() => setTab('raw')}>
              Raw
            </button>
          </div>

          {tab === 'preview' ? (
            <div className="result-content result-preview">
              {contentType === 'json' && parsed ? (
                <StructuredView data={parsed} />
              ) : contentType === 'markdown' ? (
                <MarkdownPreview content={current.content} />
              ) : (
                <pre>{current.content}</pre>
              )}
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


function MarkdownPreview({ content }: { content: string }) {
  // Simple markdown-to-HTML renderer for common patterns
  const html = markdownToHtml(content)
  return <div className="md-preview" dangerouslySetInnerHTML={{ __html: html }} />
}


function markdownToHtml(md: string): string {
  const lines = md.split('\n')
  const out: string[] = []
  let inParagraph = false

  const inline = (text: string): string => {
    return text
      // Bold
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      // Italic
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      // Inline code
      .replace(/`(.+?)`/g, '<code>$1</code>')
      // Links
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
  }

  const closeParagraph = () => {
    if (inParagraph) {
      out.push('</p>')
      inParagraph = false
    }
  }

  for (const line of lines) {
    const trimmed = line.trim()

    // Headings
    const headingMatch = trimmed.match(/^(#{1,6})\s+(.+)$/)
    if (headingMatch) {
      closeParagraph()
      const level = headingMatch[1].length
      out.push(`<h${level}>${inline(headingMatch[2])}</h${level}>`)
      continue
    }

    // Horizontal rule
    if (trimmed === '---' || trimmed === '***' || trimmed === '___') {
      closeParagraph()
      out.push('<hr />')
      continue
    }

    // Empty line
    if (!trimmed) {
      closeParagraph()
      continue
    }

    // Regular text - collect into paragraphs
    if (!inParagraph) {
      out.push('<p>')
      inParagraph = true
    } else {
      out.push(' ')
    }
    out.push(inline(trimmed))
  }

  closeParagraph()
  return out.join('\n')
}


function StructuredView({ data }: { data: Record<string, unknown> }) {
  const meta = data.metadata as Record<string, unknown> | undefined

  // If no metadata structure, show formatted JSON
  if (!meta) {
    return <pre>{JSON.stringify(data, null, 2)}</pre>
  }

  const title = meta.title ? String(meta.title) : ''
  const journal = meta.journal_or_series ? String(meta.journal_or_series) : ''
  const doi = meta.doi ? String(meta.doi) : ''
  const abstract = meta.abstract ? String(meta.abstract) : ''
  const authors = Array.isArray(meta.authors) ? (meta.authors as string[]) : []
  const confidence = meta.extraction_confidence as Record<string, number> | undefined
  const figures = Array.isArray(meta.figures) ? (meta.figures as Array<{ number: number; caption: string }>) : []
  const pages = Array.isArray(data.pages) ? (data.pages as Array<{ page_number: number; text: string }>) : []

  return (
    <div className="structured-view">
      {/* Metadata section */}
      <div className="sv-section">
        <div className="sv-section-title">Metadata</div>
        {title && (
          <div className="sv-field">
            <span className="sv-label">Title</span>
            <span className="sv-value sv-title">{title}</span>
            {confidence?.title != null && <ConfBadge value={confidence.title} />}
          </div>
        )}
        {authors.length > 0 && (
          <div className="sv-field">
            <span className="sv-label">Authors</span>
            <span className="sv-value">{authors.join(', ')}</span>
            {confidence?.authors != null && <ConfBadge value={confidence.authors} />}
          </div>
        )}
        {journal && (
          <div className="sv-field">
            <span className="sv-label">Journal</span>
            <span className="sv-value">{journal}</span>
            {confidence?.journal_or_series != null && <ConfBadge value={confidence.journal_or_series} />}
          </div>
        )}
        {doi && (
          <div className="sv-field">
            <span className="sv-label">DOI</span>
            <span className="sv-value">
              <a href={`https://doi.org/${doi}`} target="_blank" rel="noopener">{doi}</a>
            </span>
            {confidence?.doi != null && <ConfBadge value={confidence.doi} />}
          </div>
        )}
      </div>

      {/* Abstract */}
      {abstract && (
        <div className="sv-section">
          <div className="sv-section-title">
            Abstract
            {confidence?.abstract != null && <ConfBadge value={confidence.abstract} />}
          </div>
          <div className="sv-abstract">{abstract}</div>
        </div>
      )}

      {/* Figures */}
      {figures.length > 0 && (
        <div className="sv-section">
          <div className="sv-section-title">Figures</div>
          {figures.map(fig => (
            <div key={fig.number} className="sv-field">
              <span className="sv-label">Fig {fig.number}</span>
              <span className="sv-value">{fig.caption}</span>
            </div>
          ))}
        </div>
      )}

      {/* Page text preview */}
      {pages.length > 0 && (
        <div className="sv-section">
          <div className="sv-section-title">Content ({pages.length} page{pages.length > 1 ? 's' : ''})</div>
          {pages.map(page => (
            <div key={page.page_number} className="sv-page">
              {pages.length > 1 && (
                <div className="sv-page-header">Page {page.page_number}</div>
              )}
              <MarkdownPreview content={page.text} />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


function ConfBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color = pct >= 80 ? 'var(--success)' : pct >= 50 ? 'var(--warning)' : 'var(--text-dim)'
  return (
    <span className="conf-badge" style={{ color, borderColor: color }}>
      {pct}%
    </span>
  )
}
