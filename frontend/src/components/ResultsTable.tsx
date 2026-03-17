interface ResultsTableProps {
  results: Record<string, unknown>[];
}

export function ResultsTable({ results }: ResultsTableProps) {
  if (!results || results.length === 0) {
    return <div className="no-results">No results to display.</div>;
  }

  const columns = Object.keys(results[0]);

  return (
    <div className="results-container">
      <div className="results-header">
        <span className="results-count">{results.length} rows</span>
      </div>
      <div className="table-wrapper">
        <table className="results-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {results.map((row, idx) => (
              <tr key={idx}>
                {columns.map((col) => (
                  <td key={col}>
                    {row[col] === null ? <span className="null-value">NULL</span> : String(row[col])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
