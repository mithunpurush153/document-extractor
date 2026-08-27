import { useState } from 'react'
import './DetectionCard.css'

/** Tiers the confidence badge's color so low-confidence detections are visually distinct at a glance. */
function confidenceTier(confidence) {
  if (confidence >= 0.8) return 'high'
  if (confidence >= 0.5) return 'medium'
  return 'low'
}

export default function DetectionCard({ imageUrl, confidence }) {
  const [imageFailed, setImageFailed] = useState(false)
  const percent = (confidence * 100).toFixed(2)
  const tier = confidenceTier(confidence)

  return (
    <div className="detection-card" data-tier={tier}>
      <div className="detection-card__image-wrap">
        {imageFailed ? (
          <span className="detection-card__image-fallback">Preview unavailable</span>
        ) : (
          <img
            src={imageUrl}
            alt="Detected region"
            className="detection-card__image"
            loading="lazy"
            onError={() => setImageFailed(true)}
          />
        )}
      </div>
      <div className="detection-card__confidence">
        <span className="detection-card__confidence-label">Confidence</span>
        <span className="detection-card__confidence-value">{percent}%</span>
      </div>
    </div>
  )
}
