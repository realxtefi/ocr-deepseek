interface Job {
  job_id: string
  status: string
  progress_percent: number
  current_file: string | null
  total_files: number
  completed_files: number
}

interface Props {
  jobs: Job[]
  onSelect: (jobId: string) => void
  selectedJobId: string | null
}

export default function JobQueue({ jobs, onSelect, selectedJobId }: Props) {
  if (jobs.length === 0) return null

  return (
    <div className="card">
      <h2>Jobs</h2>
      {jobs.map(job => (
        <div
          key={job.job_id}
          className="job-item"
          style={{
            cursor: 'pointer',
            borderLeft: selectedJobId === job.job_id ? '3px solid var(--accent)' : '3px solid transparent',
          }}
          onClick={() => onSelect(job.job_id)}
        >
          <div className="info">
            <div className="file-name">
              {job.current_file
                ? job.current_file.split(/[\\/]/).pop()
                : `Job ${job.job_id.slice(0, 8)}`}
            </div>
            <div className="status-text">
              {job.status === 'processing'
                ? `Processing ${job.completed_files}/${job.total_files} files...`
                : job.status === 'completed'
                  ? `Completed ${job.completed_files}/${job.total_files} files`
                  : job.status}
            </div>
          </div>
          <div style={{ width: 100 }}>
            <div className="progress-bar">
              <div className="fill" style={{ width: `${job.progress_percent}%` }} />
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', textAlign: 'center' }}>
              {Math.round(job.progress_percent)}%
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
