import { useCallback, useEffect, useRef, useState } from 'react'
import FileUpload from '../components/FileUpload'
import JobQueue from '../components/JobQueue'
import ModelStatus from '../components/ModelStatus'
import ResultViewer from '../components/ResultViewer'
import SettingsPanel from '../components/SettingsPanel'
import { getJob, getStatus, processFile } from '../api'

interface JobInfo {
  job_id: string
  status: string
  progress_percent: number
  current_file: string | null
  total_files: number
  completed_files: number
}

export default function ProcessPage() {
  const [files, setFiles] = useState<File[]>([])
  const [settings, setSettings] = useState({
    output_format: 'json',
    ocr_mode: 'layout',
    pages: '',
    scientific: true,
    workers: 1,
  })
  const [jobs, setJobs] = useState<JobInfo[]>([])
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)
  const [modelReady, setModelReady] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Check model status
  useEffect(() => {
    const check = async () => {
      try {
        const status = await getStatus()
        setModelReady(status.model_loaded)
      } catch { /* ignore */ }
    }
    check()
    const interval = setInterval(check, 5000)
    return () => clearInterval(interval)
  }, [])

  // Poll active jobs
  const pollJobs = useCallback(async () => {
    const active = jobs.filter(j => j.status === 'processing' || j.status === 'queued')
    if (active.length === 0) {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
      return
    }

    for (const job of active) {
      try {
        const updated = await getJob(job.job_id)
        setJobs(prev => prev.map(j => j.job_id === job.job_id ? updated : j))
        if (updated.status === 'completed' || updated.status === 'failed') {
          setProcessing(false)
          setSelectedJobId(updated.job_id)
        }
      } catch { /* ignore */ }
    }
  }, [jobs])

  useEffect(() => {
    const hasActive = jobs.some(j => j.status === 'processing' || j.status === 'queued')
    if (hasActive && !pollRef.current) {
      pollRef.current = setInterval(pollJobs, 1500)
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [jobs, pollJobs])

  const handleProcess = async () => {
    if (files.length === 0 || !modelReady) return
    setProcessing(true)

    for (const file of files) {
      try {
        const result = await processFile(file, {
          output_format: settings.output_format,
          ocr_mode: settings.ocr_mode,
          pages: settings.pages || undefined,
          scientific: settings.scientific,
        })

        if (result.job_id) {
          const jobInfo: JobInfo = {
            job_id: result.job_id,
            status: 'processing',
            progress_percent: 0,
            current_file: file.name,
            total_files: 1,
            completed_files: 0,
          }
          setJobs(prev => [...prev, jobInfo])
          setSelectedJobId(result.job_id)
        }
      } catch (err) {
        console.error('Process error:', err)
      }
    }

    if (!pollRef.current) {
      pollRef.current = setInterval(pollJobs, 1500)
    }
  }

  return (
    <div className="process-layout">
      {/* Left column: controls */}
      <div className="process-controls">
        <ModelStatus />

        <div className="card compact">
          <h2>Upload</h2>
          <FileUpload files={files} onFilesChange={setFiles} />
        </div>

        <div className="card compact">
          <h2>Options</h2>
          <SettingsPanel settings={settings} onChange={setSettings} />
          <div style={{ marginTop: 12 }}>
            <button
              className="btn btn-primary"
              onClick={handleProcess}
              disabled={files.length === 0 || !modelReady || processing}
              style={{ width: '100%' }}
            >
              {processing ? 'Processing...' : `Process ${files.length} file(s)`}
            </button>
            {!modelReady && (
              <p style={{ fontSize: '0.8rem', color: 'var(--warning)', marginTop: 6, textAlign: 'center' }}>
                Load the model first
              </p>
            )}
          </div>
        </div>

        <JobQueue jobs={jobs} onSelect={setSelectedJobId} selectedJobId={selectedJobId} />
      </div>

      {/* Right column: results */}
      <div className="process-results">
        {selectedJobId ? (
          <ResultViewer jobId={selectedJobId} />
        ) : (
          <div className="card" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 300 }}>
            <p style={{ color: 'var(--text-dim)', textAlign: 'center' }}>
              Upload a document and click Process<br />to see results here
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
