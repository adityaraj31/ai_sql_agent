import { useState } from 'react';
import { Copy, Check, AlertTriangle } from 'lucide-react';
import { ResultsTable } from './ResultsTable';
import { ResultsChart } from './ResultsChart';
import type { ChatMessage as ChatMessageType, ChartConfig } from '../types';

interface ChatMessageProps {
  message: ChatMessageType;
  previousQuestion?: string;
}

export function ChatMessage({ message, previousQuestion }: ChatMessageProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!message.sql) return;
    try {
      await navigator.clipboard.writeText(message.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Out of Scope: Show alert box when question is irrelevant
  if (message.is_relevant === false) {
    return (
      <div className="message message-assistant">
        <div className="message-content">
          <div className="out-of-scope-alert">
            <AlertTriangle size={20} />
            <div className="out-of-scope-content">
              <strong>Out of Scope</strong>
              <p>{message.content || 'This question is outside the scope of the database. I can only answer questions about the connected database.'}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // User message
  if (message.role === 'user') {
    return (
      <div className="message message-user">
        <div className="message-content">
          <p>{message.content}</p>
        </div>
      </div>
    );
  }

  // Assistant message with SQL and/or results
  return (
    <div className="message message-assistant">
      <div className="message-content">
        {message.sql && (
          <div className="sql-query">
            <div className="sql-header">
              <span className="sql-label">Generated SQL:</span>
              <button className="copy-btn" onClick={handleCopy} title="Copy SQL">
                {copied ? <Check size={16} /> : <Copy size={16} />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <pre>{message.sql}</pre>
          </div>
        )}

        {message.content && <p>{message.content}</p>}

        {message.results && message.results.length > 0 && (
          <>
            <ResultsTable results={message.results} />
            {(() => {
              const chartConfig = analyzeForChart(message.results!, previousQuestion || '');
              if (chartConfig) {
                return <ResultsChart data={message.results!} config={chartConfig} />;
              }
              return null;
            })()}
          </>
        )}
      </div>
    </div>
  );
}

function analyzeForChart(
  results: Record<string, unknown>[],
  question: string
): ChartConfig | null {
  if (!results || results.length < 2) {
    const numericCols = results?.[0]
      ? Object.keys(results[0]).filter((k) => typeof results[0][k] === 'number')
      : [];
    if (results?.length === 1 && numericCols.length >= 2) {
      return {
        chart_type: 'bar',
        x_axis: '__columns__',
        y_axis: '__values__',
        title: 'Comparison',
      };
    }
    return null;
  }

  const columns = Object.keys(results[0]);
  const numericColumns = columns.filter((col) =>
    results.some((row) => typeof row[col] === 'number')
  );
  const stringColumns = columns.filter((col) =>
    results.some((row) => typeof row[col] === 'string')
  );

  const questionLower = question.toLowerCase();
  const hasTimeKeywords = ['date', 'year', 'month', 'quarter', 'time', 'day', 'week'].some(
    (kw) => questionLower.includes(kw)
  );

  if (hasTimeKeywords && stringColumns.length > 0) {
    return {
      chart_type: 'line',
      x_axis: stringColumns[0],
      y_axis: numericColumns[0] || stringColumns[1] || columns[1],
      title: 'Trend',
    };
  }

  if (numericColumns.length >= 2) {
    return {
      chart_type: 'scatter',
      x_axis: stringColumns[0] || columns[0],
      y_axis: numericColumns[0],
      title: 'Correlation',
    };
  }

  if (stringColumns.length > 0 && numericColumns.length > 0) {
    return {
      chart_type: 'bar',
      x_axis: stringColumns[0],
      y_axis: numericColumns[0],
      title: 'Distribution',
    };
  }

  return null;
}
