import './ErrorState.css'

export default function ErrorState({ message, onRetry }) {
  return (
    <div className="error-state" role="alert">
      <div className="error-state__label">Extraction failed</div>
      <p className="error-state__message">{message}</p>
      {onRetry && (
        <button className="btn btn--ghost" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}
