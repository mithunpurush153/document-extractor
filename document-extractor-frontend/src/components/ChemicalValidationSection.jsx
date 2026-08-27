import './ChemicalValidationSection.css'

export default function ChemicalValidationSection({ chemicalValidation }) {
  if (!chemicalValidation) return null

  if (chemicalValidation.error) {
    // Missing/non-A194 chemistry is not an extraction failure. Keep the main
    // document result intact and simply omit the document-level section.
    return null
  }

  const { identified_standard, identified_grade, reference, validation_result } = chemicalValidation
  if (!validation_result?.elements) return null

  const elements = validation_result.elements
  const summary = validation_result.summary || {}
  const hasFailures = summary.fail > 0
  const overall = hasFailures ? 'FAIL' : 'PASS'

  return (
    <section className="chemical-validation">
      <div className="chemical-validation__header">
        <div>
          <p className="chemical-validation__eyebrow">DOCUMENT-LEVEL VALIDATION</p>
          <h2 className="chemical-validation__title">Chemical Requirements</h2>
        </div>
        <div className={`chemical-validation__overall chemical-validation__overall--${overall.toLowerCase()}`}>
          <span>{overall === 'PASS' ? '✓' : '✕'}</span>
          {overall}
        </div>
      </div>

      <div className="chemical-validation__meta">
        <div><span>Material Standard</span><strong>{identified_standard}</strong></div>
        <div><span>Grade</span><strong>{identified_grade}</strong></div>
        <div><span>Reference</span><strong>{reference}</strong></div>
      </div>

      <div className="chemical-validation__summary">
        <div><strong>{summary.pass ?? 0}</strong><span>PASS</span></div>
        <div><strong>{summary.fail ?? 0}</strong><span>FAIL</span></div>
        <div><strong>{summary.not_reported ?? 0}</strong><span>NOT REPORTED</span></div>
      </div>

      <div className="chemical-validation__table-wrap">
        <table className="chemical-validation__table">
          <thead>
            <tr><th>Element</th><th>Observed</th><th>Standard Required</th><th>Status</th></tr>
          </thead>
          <tbody>
            {elements.map((element, index) => (
              <tr key={`${element.element}-${index}`}>
                <td><strong>{element.element}</strong>{element.symbol && <small>{element.symbol}</small>}</td>
                <td className="chemical-validation__observed">
                  {element.observed !== null && element.observed !== undefined
                    ? Number(element.observed).toFixed(4)
                    : '—'}
                </td>
                <td>{element.requirement_text || 'Not reported'}</td>
                <td><span className={`chemical-validation__badge chemical-validation__badge--${element.status.toLowerCase()}`}>{element.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {summary.not_reported > 0 && (
        <p className="chemical-validation__note">
          Some elements are not reported by the supplier. They are shown as NOT REPORTED and are not treated as a chemical failure.
        </p>
      )}
    </section>
  )
}