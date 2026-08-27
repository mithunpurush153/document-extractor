import { useRef, useState } from 'react'
import { ChemicalValidationApiError, validateChemicalDocuments } from '../api/chemicalValidationApi'
import './LiveChemicalValidationPanel.css'

function PdfPicker({ label, hint, file, onSelect, disabled }) {
  const inputRef = useRef(null)

  function pick(files) {
    const selected = files?.[0]
    if (!selected) return
    if (selected.type !== 'application/pdf') return
    onSelect(selected)
  }

  return (
    <div className="live-validation__picker">
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        onChange={(event) => pick(event.target.files)}
        disabled={disabled}
        hidden
      />
      <div className="live-validation__picker-label">{label}</div>
      <div className="live-validation__picker-hint">{hint}</div>
      <div className="live-validation__picker-row">
        <button
          type="button"
          className="live-validation__choose"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
        >
          {file ? 'Choose different PDF' : 'Choose PDF'}
        </button>
        {file && <span className="live-validation__filename" title={file.name}>{file.name}</span>}
      </div>
      {file && <div className="live-validation__filesize">{(file.size / (1024 * 1024)).toFixed(2)} MB</div>}
    </div>
  )
}

function formatNumber(value) {
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(2) : value
}

function formatStandardRequired(requirementText) {
  const text = String(requirementText || '').trim()

  const maxMatch = text.match(/^<=\s*(.+)$/)
  if (maxMatch) {
    return `${formatNumber(maxMatch[1])} max`
  }

  const minMatch = text.match(/^>=\s*(.+)$/)
  if (minMatch) {
    return `${formatNumber(minMatch[1])} min`
  }

  // Format ranges such as "16 - 18" as "16.00 - 18.00".
  const rangeMatch = text.match(/^([+-]?\d+(?:\.\d+)?)\s*-\s*([+-]?\d+(?:\.\d+)?)$/)
  if (rangeMatch) {
    return `${formatNumber(rangeMatch[1])} - ${formatNumber(rangeMatch[2])}`
  }

  // Preserve any remaining text, while formatting standalone numeric limits.
  return text.replace(/\d+(?:\.\d+)?/g, (value) => formatNumber(value))
}

export default function LiveChemicalValidationPanel() {
  const [referencePdf, setReferencePdf] = useState(null)
  const [testPdf, setTestPdf] = useState(null)
  const [status, setStatus] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function handleValidate() {
    if (!referencePdf || !testPdf) return
    setStatus('loading')
    setResult(null)
    setError('')

    try {
      const data = await validateChemicalDocuments(referencePdf, testPdf)
      setResult(data)
      setStatus('success')
    } catch (err) {
      setError(err instanceof ChemicalValidationApiError ? err.message : 'Validation failed.')
      setStatus('error')
    }
  }

  const validation = result?.validation_result
  const summary = validation?.summary
  const isPass = validation?.overall_status === 'PASS'

  const headerStyle = {
    fontSize: '16px',
    fontWeight: 800,
    color: '#111827',
    textAlign: 'left',
  }

  return (
    <section className="live-validation">
      <div className="live-validation__header">
        <div>
          <p className="live-validation__eyebrow">RUNTIME DOCUMENT VALIDATION</p>
          <h2>Chemical Validation</h2>
          <p>Upload the applicable standard and the supplier/test report. Both documents are extracted at runtime.</p>
        </div>
        <span className="live-validation__tag">REFERENCE + TEST</span>
      </div>

      <div className="live-validation__pickers">
        <PdfPicker
          label="Reference / Standard PDF"
          hint="The specification document containing the chemical requirements."
          file={referencePdf}
          onSelect={(file) => { setReferencePdf(file); setResult(null); setStatus('idle') }}
          disabled={status === 'loading'}
        />
        <PdfPicker
          label="Test / Supplier Report PDF"
          hint="The certificate containing the observed chemical composition."
          file={testPdf}
          onSelect={(file) => { setTestPdf(file); setResult(null); setStatus('idle') }}
          disabled={status === 'loading'}
        />
      </div>

      {error && <div className="live-validation__error">{error}</div>}

      <button
        type="button"
        className="live-validation__validate"
        onClick={handleValidate}
        disabled={!referencePdf || !testPdf || status === 'loading'}
      >
        {status === 'loading' ? 'Validating…' : 'VALIDATE'}
      </button>

      {status === 'success' && validation && (
        <div className="live-validation__result">
          <div className={`live-validation__result-banner live-validation__result-banner--${isPass ? 'pass' : 'fail'}`}>
            <div>
              <div className="live-validation__result-eyebrow">VALIDATION RESULT</div>
              <div className="live-validation__result-status">{isPass ? '✓ PASS' : '✕ FAIL'}</div>
            </div>
            <div className="live-validation__result-meta">
              <span>{result.standard}</span>
              <strong>Grade {result.grade}</strong>
            </div>
          </div>

          <div className="live-validation__doc-grid">
            <div><span>Reference</span><strong>{result.reference_filename}</strong></div>
            <div><span>Test Report</span><strong>{result.test_filename}</strong></div>
            <div><span>Standard</span><strong>{result.standard}</strong></div>
            <div><span>Grade</span><strong>{result.grade}</strong></div>
          </div>

          <div className="live-validation__summary">
            <div><strong>{summary?.pass ?? 0}</strong><span>PASS</span></div>
            <div><strong>{summary?.fail ?? 0}</strong><span>FAIL</span></div>
            <div><strong>{summary?.not_reported ?? 0}</strong><span>NOT REPORTED</span></div>
          </div>

          <div className="live-validation__table-wrap">
            <table className="live-validation__table">
              <thead>
                <tr>
                  <th style={headerStyle}>Element</th>
                  <th style={headerStyle}>Observed</th>
                  <th style={headerStyle}>Standard Requirement</th>
                  <th style={headerStyle}>Status</th>
                </tr>
              </thead>
              <tbody>
                {(validation.elements || []).map((element, index) => (
                  <tr key={`${element.element}-${index}`}>
                    <td><strong>{element.element}</strong><small>{element.symbol}</small></td>
                    <td>{element.observed == null ? '—' : Number(element.observed).toFixed(4)}</td>
                    <td>{formatStandardRequired(element.requirement_text)}</td>
                    <td><span className={`live-validation__badge live-validation__badge--${element.status.toLowerCase()}`}>{element.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  )
}