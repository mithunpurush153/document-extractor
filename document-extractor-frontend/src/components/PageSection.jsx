import TableBlock from './TableBlock'
import DetectionSection from './DetectionSection'
import './PageSection.css'

export default function PageSection({ pageLabel, pageNumber, tables, detections }) {
  return (
    <section className="page-section">
      <div className="page-section__heading">
        <span className="page-section__number">{String(pageNumber).padStart(2, '0')}</span>
        <h2 className="page-section__title">{pageLabel}</h2>
        <span className="page-section__count">
          {tables.length} {tables.length === 1 ? 'table' : 'tables'}
        </span>
      </div>

      {tables.length === 0 ? (
        <p className="page-section__none">No tables detected on this page.</p>
      ) : (
        <div className="page-section__tables">
          {tables.map((table, i) => (
            <TableBlock key={i} table={table} index={i} />
          ))}
        </div>
      )}

      <DetectionSection detections={detections} />
    </section>
  )
}
