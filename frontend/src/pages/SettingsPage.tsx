import { useEffect, useState } from 'react'
import ModelStatus from '../components/ModelStatus'
import { getConfig, updateConfig } from '../api'

export default function SettingsPage() {
  const [config, setConfig] = useState<Record<string, Record<string, unknown>> | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getConfig()
        setConfig(data)
      } catch {
        setMessage('Failed to load config')
      }
    }
    load()
  }, [])

  const handleSave = async () => {
    if (!config) return
    setSaving(true)
    try {
      const updated = await updateConfig({
        processing: config.processing,
        converter: config.converter,
        output: config.output,
      })
      setConfig(updated)
      setMessage('Settings saved')
      setTimeout(() => setMessage(''), 2000)
    } catch {
      setMessage('Failed to save')
    }
    setSaving(false)
  }

  const updateField = (section: string, key: string, value: unknown) => {
    if (!config) return
    setConfig({
      ...config,
      [section]: { ...config[section], [key]: value },
    })
  }

  return (
    <div>
      <ModelStatus />

      <div className="card">
        <h2>Processing Defaults</h2>
        {config && (
          <div className="settings-grid">
            <div className="form-group">
              <label>Default Output Format</label>
              <select
                value={String(config.processing?.default_output_format || 'json')}
                onChange={e => updateField('processing', 'default_output_format', e.target.value)}
              >
                <option value="json">JSON</option>
                <option value="markdown">Markdown</option>
                <option value="xml">XML</option>
              </select>
            </div>

            <div className="form-group">
              <label>Default OCR Mode</label>
              <select
                value={String(config.processing?.default_ocr_mode || 'layout')}
                onChange={e => updateField('processing', 'default_ocr_mode', e.target.value)}
              >
                <option value="layout">Layout (Markdown)</option>
                <option value="plain">Plain Text</option>
                <option value="ocr">OCR (Grounded)</option>
                <option value="figure">Parse Figure</option>
                <option value="describe">Describe Image</option>
              </select>
            </div>

            <div className="form-group">
              <label>Default Workers</label>
              <input
                type="number"
                min={1}
                max={8}
                value={Number(config.processing?.workers || 1)}
                onChange={e => updateField('processing', 'workers', parseInt(e.target.value) || 1)}
              />
            </div>

            <div className="form-group">
              <label>PDF Render DPI</label>
              <input
                type="number"
                min={72}
                max={600}
                step={50}
                value={Number(config.processing?.pdf_dpi || 300)}
                onChange={e => updateField('processing', 'pdf_dpi', parseInt(e.target.value) || 300)}
              />
            </div>

            <div className="form-group">
              <label>Output Directory</label>
              <input
                type="text"
                value={String(config.output?.default_dir || './output')}
                onChange={e => updateField('output', 'default_dir', e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>DOCX Conversion Method</label>
              <select
                value={String(config.converter?.docx_method || 'auto')}
                onChange={e => updateField('converter', 'docx_method', e.target.value)}
              >
                <option value="auto">Auto-detect</option>
                <option value="libreoffice">LibreOffice</option>
                <option value="comtypes">Microsoft Word (COM)</option>
              </select>
            </div>
          </div>
        )}

        <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          {message && (
            <span style={{ fontSize: '0.85rem', color: 'var(--text-dim)' }}>{message}</span>
          )}
        </div>
      </div>
    </div>
  )
}
