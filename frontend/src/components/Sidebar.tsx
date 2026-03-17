import { Plus, Trash2, Database, RefreshCw, Loader2, CheckCircle, XCircle, MessageSquare, X } from 'lucide-react';
import type { QueryLog } from '../types';

interface SidebarProps {
  history: QueryLog[];
  onNewChat: () => void;
  onClearHistory: () => void;
  onCreateEmbeddings: () => void;
  isCreatingEmbeddings: boolean;
  embeddingStatus: string;
  onHistoryClick: (session: QueryLog) => void;
  onDeleteSession: (sessionId: string, e: React.MouseEvent) => void;
}

export function Sidebar({
  history,
  onNewChat,
  onClearHistory,
  onCreateEmbeddings,
  isCreatingEmbeddings,
  embeddingStatus,
  onHistoryClick,
  onDeleteSession,
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
          disabled={isCreatingEmbeddings || embeddingStatus === 'in_progress'}
          title="Rebuild schema graph"
        >
          {isCreatingEmbeddings || embeddingStatus === 'in_progress' ? (
            <Loader2 size={16} className="spin" />
          ) : embeddingStatus === 'completed' ? (
            <CheckCircle size={16} />
          ) : embeddingStatus === 'failed' ? (
            <XCircle size={16} />
          ) : (
            <RefreshCw size={16} />
          )}
          {isCreatingEmbeddings || embeddingStatus === 'in_progress'
            ? 'Building...'
            : embeddingStatus === 'completed'
            ? 'Ready ✓'
            : embeddingStatus === 'failed'
            ? 'Failed ✗'
            : 'Create Embeddings'}
        </button>
      </div>

      <div className="sidebar-divider" />

      <div className="sidebar-section">
        <h3 className="sidebar-title">
          <Database size={16} />
          History
        </h3>
        
        {history.length === 0 ? (
          <p className="sidebar-empty">No chat sessions yet.</p>
        ) : (
          <ul className="history-list">
            {history.slice(0, 10).reverse().map((log, index) => (
              <li key={index} className="history-item">
                <button
                  className="history-btn"
                  onClick={() => onHistoryClick(log)}
                  title={log.title || 'Chat Session'}
                >
                  <MessageSquare size={14} />
                  <span className="history-question">
                    {(log.title || 'New Chat').length > 20
                      ? (log.title || 'New Chat').slice(0, 17) + '...'
                      : log.title || 'New Chat'}
                  </span>
                </button>
                <button
                  className="history-delete-btn"
                  onClick={(e) => onDeleteSession(log.session_id, e)}
                  title="Delete session"
                >
                  <X size={12} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
