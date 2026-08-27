import DetectionCard from './DetectionCard'
import { getCropUrl } from '../api/extractorApi'
import './DetectionSection.css'

function DetectionGroup({ title, items, emptyLabel }) {
  return (
    <div className="detection-group">
      <div className="detection-group__header">
        <span className="detection-group__title">{title}</span>
        <span className="detection-group__count">{items.length}</span>
      </div>

      {items.length === 0 ? (
        <p className="detection-group__empty">{emptyLabel}</p>
      ) : (
        <div className="detection-group__grid">
          {items.map((item, i) => (
            <DetectionCard key={i} imageUrl={getCropUrl(item.image_url)} confidence={item.confidence} />
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * `detections` is one page's entry from detections_by_page — may be
 * undefined entirely (older/partial responses) or have empty arrays;
 * both are handled the same way, via the ?? [] fallbacks below.
 */
export default function DetectionSection({ detections }) {
  const stamps = detections?.stamps ?? []
  const signatures = detections?.signatures ?? []

  return (
    <div className="detection-section">
      <div className="detection-section__header">
        <span className="detection-section__icon" aria-hidden="true" />
        <h3 className="detection-section__title">AI Detections</h3>
      </div>

      <div className="detection-section__groups">
        <DetectionGroup title="Stamps" items={stamps} emptyLabel="No stamps detected" />
        <DetectionGroup title="Signatures" items={signatures} emptyLabel="No signatures detected" />
      </div>
    </div>
  )
}
