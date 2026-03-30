const BASE = '/api/v1'

async function request(path: string, options?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, options)
  return res.json()
}

export async function getStatus() {
  return request('/status')
}

export async function downloadModel() {
  return request('/model/download', { method: 'POST' })
}

export async function loadModel(device = 'auto') {
  return request('/model/load', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device }),
  })
}

export async function processFile(
  file: File,
  options: {
    output_format?: string
    ocr_mode?: string
    pages?: string
    scientific?: boolean
  } = {}
) {
  const form = new FormData()
  form.append('file', file)
  form.append('output_format', options.output_format || 'json')
  form.append('ocr_mode', options.ocr_mode || 'layout')
  if (options.pages) form.append('pages', options.pages)
  form.append('scientific', String(options.scientific ?? true))

  return request('/process/file', { method: 'POST', body: form })
}

export async function processFolder(options: {
  folder_path: string
  recursive?: boolean
  output_format?: string
  ocr_mode?: string
  pages?: string
  scientific?: boolean
  workers?: number
  output_dir?: string
}) {
  return request('/process/folder', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options),
  })
}

export async function getJob(jobId: string) {
  return request(`/jobs/${jobId}`)
}

export async function getJobResult(jobId: string) {
  return request(`/jobs/${jobId}/result`)
}

export async function listJobs() {
  return request('/jobs')
}

export async function cancelJob(jobId: string) {
  return request(`/jobs/${jobId}`, { method: 'DELETE' })
}

export async function getConfig() {
  return request('/config')
}

export async function updateConfig(config: Record<string, unknown>) {
  return request('/config', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
}
