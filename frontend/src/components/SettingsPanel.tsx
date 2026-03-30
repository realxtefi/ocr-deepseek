interface Settings {
  output_format: string
  ocr_mode: string
  pages: string
  scientific: boolean
  workers: number
}

interface Props {
  settings: Settings
  onChange: (settings: Settings) => void
}

export default function SettingsPanel({ settings, onChange }: Props) {
  const update = (key: keyof Settings, value: string | boolean | number) => {
    onChange({ ...settings, [key]: value })
  }

  return (
    <div className="settings-compact">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <div className="form-group">
          <label>Format</label>
          <select
            value={settings.output_format}
            onChange={e => update('output_format', e.target.value)}
          >
            <option value="json">JSON</option>
            <option value="markdown">Markdown</option>
            <option value="xml">XML</option>
          </select>
        </div>

        <div className="form-group">
          <label>OCR Mode</label>
          <select
            value={settings.ocr_mode}
            onChange={e => update('ocr_mode', e.target.value)}
          >
            <option value="layout">Layout</option>
            <option value="plain">Plain</option>
          </select>
        </div>

        <div className="form-group">
          <label>PDF Pages</label>
          <input
            type="text"
            placeholder="All (e.g. 1-3,5)"
            value={settings.pages}
            onChange={e => update('pages', e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Workers</label>
          <input
            type="number"
            min={1}
            max={8}
            value={settings.workers}
            onChange={e => update('workers', parseInt(e.target.value) || 1)}
          />
        </div>
      </div>

      <div className="form-group" style={{ marginTop: 8 }}>
        <label>
          <input
            type="checkbox"
            checked={settings.scientific}
            onChange={e => update('scientific', e.target.checked)}
            style={{ marginRight: 6 }}
          />
          Scientific Extraction
        </label>
      </div>
    </div>
  )
}
