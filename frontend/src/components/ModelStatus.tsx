import { useEffect, useState } from 'react'
import { getStatus, downloadModel, loadModel } from '../api'

interface Status {
  model_downloaded: boolean
  model_loaded: boolean
  device: string | null
  cuda_available: boolean
  gpu_name: string | null
  vram_total_mb: number | null
  vram_used_mb: number | null
  downloading: boolean
  download_progress: number
}

export default function ModelStatus() {
  const [status, setStatus] = useState<Status | null>(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [selectedDevice, setSelectedDevice] = useState('auto')

  const fetchStatus = async () => {
    try {
      const data = await getStatus()
      setStatus(data)
    } catch {
      setMessage('Failed to connect to backend')
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 3000)
    return () => clearInterval(interval)
  }, [])

  const handleDownload = async () => {
    setLoading(true)
    setMessage('Downloading model...')
    try {
      await downloadModel()
      setMessage('Download started. This may take a while (~6GB).')
      const poll = setInterval(async () => {
        const s = await getStatus()
        setStatus(s)
        if (s.model_downloaded && !s.downloading) {
          clearInterval(poll)
          setMessage('Model downloaded!')
          setLoading(false)
        }
      }, 2000)
    } catch {
      setMessage('Download failed')
      setLoading(false)
    }
  }

  const handleLoad = async (device?: string) => {
    const deviceToUse = device || selectedDevice
    setLoading(true)
    setMessage(`Loading model on ${deviceToUse === 'auto' ? 'best available device' : deviceToUse.toUpperCase()}...`)
    try {
      const result = await loadModel(deviceToUse)
      if (result.success) {
        setMessage(`Model loaded on ${result.device.toUpperCase()}`)
      } else {
        setMessage(`Load failed: ${result.message}`)
      }
      await fetchStatus()
    } catch {
      setMessage('Load failed')
    }
    setLoading(false)
  }

  const handleUnload = async () => {
    setLoading(true)
    setMessage('Unloading model...')
    try {
      await fetch('/api/v1/model/unload', { method: 'POST' })
      setMessage('Model unloaded')
      await fetchStatus()
    } catch {
      setMessage('Unload failed')
    }
    setLoading(false)
  }

  const handleSwitchDevice = async (device: string) => {
    setSelectedDevice(device)
    if (status?.model_loaded) {
      await handleLoad(device)
    }
  }

  if (!status) {
    return (
      <div className="card">
        <h2>Model Status</h2>
        <p style={{ color: 'var(--text-dim)' }}>{message || 'Connecting...'}</p>
      </div>
    )
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h2>Model Status</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {status.model_loaded && (
            <span className={`status-badge ${status.device === 'cuda' ? 'gpu' : 'cpu'}`}>
              {status.device === 'cuda'
                ? `GPU: ${status.gpu_name || 'CUDA'}`
                : 'CPU Mode'}
            </span>
          )}
          {!status.model_loaded && !loading && (
            <span className="status-badge error">Not Loaded</span>
          )}
          {loading && <span className="status-badge loading">Working...</span>}
        </div>
      </div>

      {status.cuda_available && status.vram_total_mb && (
        <p style={{ fontSize: '0.85rem', color: 'var(--text-dim)', marginBottom: 8 }}>
          VRAM: {status.vram_used_mb || 0} / {status.vram_total_mb} MB
        </p>
      )}

      {!status.cuda_available && (
        <p style={{ fontSize: '0.85rem', color: 'var(--text-dim)', marginBottom: 8 }}>
          No CUDA GPU detected. Running in CPU-only mode (slower but fully functional).
        </p>
      )}

      {/* Device selector */}
      {status.model_downloaded && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>Device:</label>
          <select
            value={selectedDevice}
            onChange={e => handleSwitchDevice(e.target.value)}
            disabled={loading}
            style={{ width: 'auto' }}
          >
            <option value="auto">Auto-detect</option>
            {status.cuda_available && <option value="cuda">GPU (CUDA)</option>}
            <option value="cpu">CPU</option>
          </select>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8 }}>
        {!status.model_downloaded && (
          <button className="btn btn-primary" onClick={handleDownload} disabled={loading}>
            Download Model (~6GB)
          </button>
        )}

        {status.model_downloaded && !status.model_loaded && (
          <button className="btn btn-primary" onClick={() => handleLoad()} disabled={loading}>
            Load Model
          </button>
        )}

        {status.model_loaded && (
          <button className="btn btn-secondary" onClick={handleUnload} disabled={loading} style={{ fontSize: '0.85rem' }}>
            Unload
          </button>
        )}
      </div>

      {message && (
        <p style={{ fontSize: '0.85rem', color: 'var(--text-dim)', marginTop: 8 }}>{message}</p>
      )}
    </div>
  )
}
