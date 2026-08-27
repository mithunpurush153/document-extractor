import './LoadingState.css'

export default function LoadingState() {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="loading-state__spinner" aria-hidden="true" />
      <span className="loading-state__text">Processing PDF…</span>
    </div>
  )
}
