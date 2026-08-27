import PageSection from './PageSection'
import ChemicalValidationSection from './ChemicalValidationSection'
import { getDownloadUrl } from '../api/extractorApi'
import './ResultsView.css'

/** "page_1" -> 1, used to sort keys numerically and to derive the page number. */
function pageNumberFromKey(key) {
  const match = key.match(/(\d+)/)
  return match ? parseInt(match[1], 10) : 0
}

export default function ResultsView({ result }) {
  const { job_id, filename, total_pages, tables_by_page, detections_by_page, chemical_validation } = result

  const orderedPageKeys = Object.keys(tables_by_page).sort(
    (a, b) => pageNumberFromKey(a) - pageNumberFromKey(b),
  )

  const totalTables = orderedPageKeys.reduce(
    (sum, key) => sum + tables_by_page[key].length,
    0,
  )

  return (
    <div className="results-view">
      <div className="results-view__summary">
        <div className="results-view__summary-text">
          <span className="results-view__filename">{filename}</span>
          <span className="results-view__meta">
            {total_pages} {total_pages === 1 ? 'page' : 'pages'} · {totalTables}{' '}
            {totalTables === 1 ? 'table' : 'tables'} detected
          </span>
        </div>
        <a
          className="btn btn--primary"
          href={getDownloadUrl(job_id)}
          download={`extracted_tables_${job_id}.json`}
        >
          Download JSON
        </a>
      </div>

      <ChemicalValidationSection chemicalValidation={chemical_validation} />

      <div className="results-view__pages">
        {orderedPageKeys.map((key) => (
          <PageSection
            key={key}
            pageLabel={`Page ${pageNumberFromKey(key)}`}
            pageNumber={pageNumberFromKey(key)}
            tables={tables_by_page[key]}
            detections={detections_by_page?.[key]}
          />
        ))}
      </div>
    </div>
  )
}
