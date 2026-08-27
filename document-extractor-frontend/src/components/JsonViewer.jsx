import { useState } from 'react'
import './JsonViewer.css'

export default function JsonViewer({ data }) {
  const [copied, setCopied] = useState(false)
  const formatted = JSON.stringify(data, null, 2)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(formatted)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // Clipboard API unavailable — fail silently, the JSON is still visible to select/copy manually
    }
  }

  return (
    <div className="json-viewer">
      <div className="json-viewer__bar">
        <span className="json-viewer__label">JSON</span>
        <button className="json-viewer__copy" onClick={handleCopy}>
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="json-viewer__pre">
        <code>{formatted}</code>
      </pre>
    </div>
  )
}
