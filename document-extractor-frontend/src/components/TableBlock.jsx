import JsonViewer from './JsonViewer'
import './TableBlock.css'

export default function TableBlock({ table, index }) {
  const { columns, data, rows, cols } = table

  return (
    <div className="table-block">
      <div className="table-block__header">
        <span className="table-block__title">Table {index + 1}</span>
        <span className="table-block__dims">
          {rows} rows × {cols} cols
        </span>
      </div>

      <div className="table-block__scroll">
        <table className="table-block__table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIdx) => (
              <tr key={rowIdx}>
                {columns.map((col) => (
                  <td key={col}>{row[col] ?? ''}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <JsonViewer data={data} />
    </div>
  )
}
