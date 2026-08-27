import { useState } from 'react'
import Header from './components/Header'
import UploadPanel from './components/UploadPanel'
import LoadingState from './components/LoadingState'
import ErrorState from './components/ErrorState'
import EmptyState from './components/EmptyState'
import ResultsView from './components/ResultsView'
import LiveChemicalValidationPanel from './components/LiveChemicalValidationPanel'
import { extractTables, ApiError } from './api/extractorApi'
import './App.css'

/** Drives which panel shows below the uploader. */
const STATUS = {
  IDLE: 'idle',
  LOADING: 'loading',
  ERROR: 'error',
  SUCCESS: 'success',
}

export default function App() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [status, setStatus] = useState(STATUS.IDLE)
  const [result, setResult] = useState(null)
  const [errorMessage, setErrorMessage] = useState('')

  function handleFileSelect(file) {
    setSelectedFile(file)
    setStatus(STATUS.IDLE)
    setResult(null)
    setErrorMessage('')
  }

  async function handleExtract() {
    if (!selectedFile) return
    setStatus(STATUS.LOADING)
    setErrorMessage('')

    try {
      const data = await extractTables(selectedFile)
      setResult(data)
      setStatus(STATUS.SUCCESS)
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : 'Something went wrong. Please try again.'
      setErrorMessage(message)
      setStatus(STATUS.ERROR)
    }
  }

  return (
    <div className="app">
      <Header />

      <LiveChemicalValidationPanel />

      <UploadPanel
        selectedFile={selectedFile}
        onFileSelect={handleFileSelect}
        onExtract={handleExtract}
        isProcessing={status === STATUS.LOADING}
      />

      <main className="app__body">
        {status === STATUS.LOADING && <LoadingState />}
        {status === STATUS.ERROR && (
          <ErrorState message={errorMessage} onRetry={handleExtract} />
        )}
        {status === STATUS.IDLE && <EmptyState />}
        {status === STATUS.SUCCESS && result && <ResultsView result={result} />}
      </main>
    </div>
  )
}
