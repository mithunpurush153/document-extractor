import './Header.css'

export default function Header() {
  return (
    <header className="header">
      <div className="header__eyebrow">PDF → structured tables</div>
      <h1 className="header__title">Document Table Extractor</h1>
      <p className="header__subtitle">
        Upload a scanned or digital PDF and pull every table out as clean,
        page-indexed JSON.
      </p>
    </header>
  )
}
