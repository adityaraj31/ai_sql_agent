import { Plus, Trash2, Database, RefreshCw, Loader2 } from 'lucide-react';
import type { QueryLog } from '../types';

interface SidebarProps {
  history: QueryLog[];
  onNewChat: () => void;
  onClearHistory: () => void;
  onCreateEmbeddings: () => void;
  isCreatingEmbeddings: boolean;
  onHistoryClick: (question: string) => void;
}

export function Sidebar({
  history,
  onNewChat,
  onClearHistory,
  onCreateEmbeddings,
  isCreatingEmbeddings,
  onHistoryClick,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={onNewChat}>
          <Plus size={18} />
          New Chat
        </button>
      </div>

      <div className="sidebar-section">
        <button
          className="sidebar-action-btn"
          onClick={onClearHistory}
          title="Clear database history"
        >
          <Trash2 size={16} />
          Clear History
        </button>

        <button
          className="sidebar-action-btn"
          onClick={onCreateEmbeddings}
          disabled={isCreatingEmbeddings}
          title="Rebuild schema graph"
        >
          {isCreatingEmbeddings ? (
            <Loader2 size={16} className="spin" />
          ) : (
            <RefreshCw size={16} />
          )}
          {isCreatingEmbeddings ? 'Building...' : 'Create Embeddings'}
        </button>
      </div>

      <div className="sidebar-divider" />

      <div className="sidebar-section">
        <h3 className="sidebar-title">
          <Database size={16} />
          History
        </h3>
        
        {history.length === 0 ? (
          <p className="sidebar-empty">No queries yet.</p>
        ) : (
          <ul className="history-list">
            {history.slice(0, 10).reverse().map((log, index) => (
              <li key={index} className="history-item">
                <button
                  className="history-btn"
                  onClick={() => onHistoryClick(log.question)}
                  title={log.question}
                >
                  <span className="history-question">
                    {log.question.length > 30
                      ? log.question.slice(0, 27) + '...'
                      : log.question}
                  </span>
                  <span className={`history-status ${log.success ? 'success' : 'error'}`}>
                    {log.success ? '✓' : '✗'}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
