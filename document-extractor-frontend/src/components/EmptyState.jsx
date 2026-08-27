import './EmptyState.css'

export default function EmptyState() {
  return (
    <div className="empty-state">
      <p className="empty-state__text">
        No results yet — upload a PDF above and select{' '}
        <span className="empty-state__accent">Extract Tables</span> to see
        every table pulled out page by page.
      </p>
    </div>
  )
}
