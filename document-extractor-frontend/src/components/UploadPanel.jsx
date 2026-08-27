import { useRef, useState } from 'react'
import './UploadPanel.css'

const ACCEPTED_TYPE = 'application/pdf'

export default function UploadPanel({ selectedFile, onFileSelect, onExtract, isProcessing }) {
  const inputRef = useRef(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [rejectionMessage, setRejectionMessage] = useState('')

  function handleFiles(fileList) {
    const file = fileList?.[0]
    if (!file) return

    if (file.type !== ACCEPTED_TYPE) {
      setRejectionMessage('Only PDF files are supported.')
      return
    }

    setRejectionMessage('')
    onFileSelect(file)
  }

  function handleDrop(e) {
    e.preventDefault()
    setIsDragOver(false)
    if (isProcessing) return
    handleFiles(e.dataTransfer.files)
  }

  return (
    <section className="upload-panel">
      <div
        className={`scan-frame ${isDragOver ? 'scan-frame--drag' : ''} ${isProcessing ? 'scan-frame--scanning' : ''}`}
        onDragOver={(e) => {
          e.preventDefault()
          if (!isProcessing) setIsDragOver(true)
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
      >
        <span className="scan-frame__corner scan-frame__corner--tl" />
        <span className="scan-frame__corner scan-frame__corner--tr" />
        <span className="scan-frame__corner scan-frame__corner--bl" />
        <span className="scan-frame__corner scan-frame__corner--br" />
        {isProcessing && <span className="scan-frame__sweep" />}

        <div className="scan-frame__content">
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf"
            onChange={(e) => handleFiles(e.target.files)}
            disabled={isProcessing}
            className="scan-frame__input"
            id="pdf-upload-input"
          />

          {selectedFile ? (
            <>
              <div className="scan-frame__filename" title={selectedFile.name}>
                {selectedFile.name}
              </div>
              <div className="scan-frame__filesize">
                {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
              </div>
              <label htmlFor="pdf-upload-input" className="btn btn--ghost">
                Choose a different file
              </label>
            </>
          ) : (
            <>
              <div className="scan-frame__hint">Drag a PDF here, or</div>
              <label htmlFor="pdf-upload-input" className="btn btn--primary">
                Choose PDF
              </label>
            </>
          )}
        </div>
      </div>

      {rejectionMessage && <p className="upload-panel__error">{rejectionMessage}</p>}

      <button
        className="btn btn--extract"
        onClick={onExtract}
        disabled={!selectedFile || isProcessing}
      >
        {isProcessing ? 'Processing…' : 'Extract Tables'}
      </button>
    </section>
  )
}
