import { useCallback, useRef, useState } from 'react'

interface Props {
  files: File[]
  onFilesChange: (files: File[]) => void
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const ACCEPTED = '.png,.jpg,.jpeg,.tiff,.tif,.bmp,.webp,.pdf,.docx'

export default function FileUpload({ files, onFilesChange }: Props) {
  const [dragover, setDragover] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const arr = Array.from(newFiles)
    const unique = arr.filter(
      f => !files.some(existing => existing.name === f.name && existing.size === f.size)
    )
    onFilesChange([...files, ...unique])
  }, [files, onFilesChange])

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragover(false)
    if (e.dataTransfer.files.length) {
      addFiles(e.dataTransfer.files)
    }
  }

  const removeFile = (index: number) => {
    onFilesChange(files.filter((_, i) => i !== index))
  }

  return (
    <div>
      <div
        className={`drop-zone ${dragover ? 'dragover' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragover(true) }}
        onDragLeave={() => setDragover(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <p>Drop files here or click to browse</p>
        <p style={{ fontSize: '0.8rem', marginTop: 4 }}>
          Supports: PNG, JPG, TIFF, BMP, WebP, PDF, DOCX
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED}
          style={{ display: 'none' }}
          onChange={e => e.target.files && addFiles(e.target.files)}
        />
      </div>

      {files.length > 0 && (
        <div className="file-list">
          {files.map((f, i) => (
            <div key={`${f.name}-${f.size}`} className="file-item">
              <span className="name">{f.name}</span>
              <span className="size">{formatSize(f.size)}</span>
              <button className="remove" onClick={() => removeFile(i)}>&times;</button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
