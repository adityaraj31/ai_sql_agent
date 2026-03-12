import { useState, useEffect, useRef } from 'react';
import { Sidebar, ChatInput, ResultsTable, ResultsChart } from './components';
import { chat, getHistory, clearHistory, createEmbeddings } from './services/api';
import type { ChatMessage, QueryLog, ChartConfig } from './types';
import './App.css';

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [history, setHistory] = useState<QueryLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreatingEmbeddings, setIsCreatingEmbeddings] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await getHistory();
      setHistory(data.logs);
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  };

  const handleSendMessage = async (question: string) => {
    const userMessage: ChatMessage = {
      role: 'user',
      content: question,
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const chatHistory = messages
        .filter((m) => m.role !== 'user' || m.content)
        .map((m) => ({
          role: m.role,
          content: m.content,
          sql: m.sql,
        }));

      const response = await chat({
        question,
        chat_history: chatHistory,
      });

      if (response.success) {
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: 'Here are the results:',
          sql: response.sql_query,
          results: response.results,
          chart: null,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        setError(response.error || response.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsLoading(false);
      loadHistory();
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setError(null);
  };

  const handleClearHistory = async () => {
    try {
      await clearHistory();
      setHistory([]);
    } catch (err) {
      console.error('Failed to clear history:', err);
    }
  };

  const handleCreateEmbeddings = async () => {
    setIsCreatingEmbeddings(true);
    try {
      await createEmbeddings();
      alert('Embedding creation started in the background. It will take 1-2 minutes.');
    } catch (err) {
      console.error('Failed to start embedding creation:', err);
      alert('Failed to start embedding creation');
    } finally {
      setIsCreatingEmbeddings(false);
    }
  };

  const handleHistoryClick = (question: string) => {
    handleSendMessage(question);
  };

  const analyzeForChart = (results: Record<string, unknown>[], question: string): ChartConfig | null => {
    if (!results || results.length < 2) {
      const numericCols = results?.[0] ? Object.keys(results[0]).filter((k) => typeof results[0][k] === 'number') : [];
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
  };

  return (
    <div className="app">
      <Sidebar
        history={history}
        onNewChat={handleNewChat}
        onClearHistory={handleClearHistory}
        onCreateEmbeddings={handleCreateEmbeddings}
        isCreatingEmbeddings={isCreatingEmbeddings}
        onHistoryClick={handleHistoryClick}
      />

      <main className="main-content">
        {messages.length === 0 ? (
          <div className="greeting">
            <h1>How can I help you with data today?</h1>
            <p>Ask anything from the Chinook database—sales, trends, or customer insights.</p>
          </div>
        ) : (
          <div className="chat-container">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message message-${msg.role}`}>
                <div className="message-content">
                  {msg.role === 'user' ? (
                    <p>{msg.content}</p>
                  ) : (
                    <>
                      {msg.sql && (
                        <div className="sql-query">
                          <span className="sql-label">Generated SQL:</span>
                          <pre>{msg.sql}</pre>
                        </div>
                      )}
                      {msg.content && <p>{msg.content}</p>}
                      {msg.results && msg.results.length > 0 && (
                        <>
                          <ResultsTable results={msg.results} />
                          {(() => {
                            const chartConfig = analyzeForChart(msg.results, messages[idx - 1]?.content || '');
                            if (chartConfig) {
                              return <ResultsChart data={msg.results} config={chartConfig} />;
                            }
                            return null;
                          })()}
                        </>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="message message-assistant">
                <div className="message-content loading">
                  <div className="spinner" />
                  <span>Analyzing request...</span>
                </div>
              </div>
            )}
            {error && (
              <div className="error-message">
                <strong>Error:</strong> {error}
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        <div className="input-area">
          <ChatInput onSend={handleSendMessage} disabled={isLoading} />
        </div>
      </main>
    </div>
  );
}

export default App;
