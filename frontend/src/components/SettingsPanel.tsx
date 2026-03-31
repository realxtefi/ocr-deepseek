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

const MODE_INFO: Record<string, { label: string; help: string }> = {
  layout: {
    label: 'Layout (Markdown)',
    help: 'Converts documents to structured Markdown preserving headings, columns, tables, and figure positions. Best for papers, reports, and multi-column documents.',
  },
  plain: {
    label: 'Plain Text',
    help: 'Extracts raw text without layout or structure. Fast and simple, best when you only need the text content.',
  },
  ocr: {
    label: 'OCR (Grounded)',
    help: 'Extracts text with bounding box coordinates for each element. Useful when you need to know where text appears on the page.',
  },
  figure: {
    label: 'Parse Figure',
    help: 'Specialized for charts, diagrams, and plots. Extracts data, labels, axes, and relationships from visual figures.',
  },
  describe: {
    label: 'Describe Image',
    help: 'Generates a detailed natural language description of the image. Best for photos, illustrations, and complex visuals.',
  },
}

export default function SettingsPanel({ settings, onChange }: Props) {
  const update = (key: keyof Settings, value: string | boolean | number) => {
    onChange({ ...settings, [key]: value })
  }

  const modeHelp = MODE_INFO[settings.ocr_mode]?.help

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
            {Object.entries(MODE_INFO).map(([value, { label }]) => (
              <option key={value} value={value}>{label}</option>
            ))}
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

      {modeHelp && (
        <div className="mode-help">
          {modeHelp}
        </div>
      )}

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
