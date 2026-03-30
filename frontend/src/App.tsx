import { useState } from 'react'
import ProcessPage from './pages/ProcessPage'
import SettingsPage from './pages/SettingsPage'

type Page = 'process' | 'settings'

export default function App() {
  const [page, setPage] = useState<Page>('process')

  return (
    <div className="app">
      <header>
        <h1>DeepSeek-OCR-2</h1>
        <nav>
          <button
            className={page === 'process' ? 'active' : ''}
            onClick={() => setPage('process')}
          >
            Process
          </button>
          <button
            className={page === 'settings' ? 'active' : ''}
            onClick={() => setPage('settings')}
          >
            Settings
          </button>
        </nav>
      </header>

      {page === 'process' && <ProcessPage />}
      {page === 'settings' && <SettingsPage />}
    </div>
  )
}
