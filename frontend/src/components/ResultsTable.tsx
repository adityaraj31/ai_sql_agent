import { Download } from 'lucide-react';

interface ResultsTableProps {
  results: Record<string, unknown>[];
}

export function ResultsTable({ results }: ResultsTableProps) {
  if (!results || results.length === 0) {
    return <div className="no-results">No results to display.</div>;
  }

  const columns = Object.keys(results[0]);

  const downloadCSV = () => {
    const headers = columns.join(',');
    const rows = results.map((row) =>
      columns.map((col) => {
        const val = row[col];
        const str = val === null || val === undefined ? '' : String(val);
        return str.includes(',') || str.includes('"') || str.includes('\n')
          ? `"${str.replace(/"/g, '""')}"`
          : str;
      }).join(',')
    );
    const csv = [headers, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'query_results.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="results-container">
      <div className="results-header">
        <span className="results-count">{results.length} rows</span>
        <button className="download-btn" onClick={downloadCSV}>
          <Download size={16} />
          Download CSV
        </button>
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
