import { useState, useEffect, useRef } from 'react';
import { Sidebar, ChatInput, ChatMessage } from './components';
import { chat, getHistory, clearHistory, createEmbeddings, getEmbeddingStatus } from './services/api';
import type { ChatMessage as ChatMessageType, QueryLog } from './types';
import './App.css';

function App() {
  const [messages, setMessages] = useState<ChatMessageType[]>([]);
  const [history, setHistory] = useState<QueryLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isCreatingEmbeddings, setIsCreatingEmbeddings] = useState(false);
  const [embeddingStatus, setEmbeddingStatus] = useState<string>('not_started');
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
    checkEmbeddingStatus();
  }, []);

  // Poll for embedding status when in progress
  useEffect(() => {
    if (embeddingStatus === 'in_progress') {
      const interval = setInterval(() => {
        checkEmbeddingStatus();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [embeddingStatus]);

  const checkEmbeddingStatus = async () => {
    try {
      const status = await getEmbeddingStatus();
      setEmbeddingStatus(status.status);
      if (status.status === 'completed') {
        alert('✅ Embedding creation completed successfully!');
      } else if (status.status === 'failed') {
        alert(`❌ Embedding creation failed: ${status.message}`);
      }
    } catch (err) {
      console.error('Failed to check embedding status:', err);
    }
  };

  const loadHistory = async () => {
    try {
      const data = await getHistory();
      setHistory(data.logs);
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  };

  const handleSendMessage = async (question: string) => {
    const userMessage: ChatMessageType = {
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
        const assistantMessage: ChatMessageType = {
          role: 'assistant',
          content: response.message,
          sql: response.sql_query,
          results: response.results,
          chart: null,
          is_relevant: response.is_relevant,
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
    setEmbeddingStatus('in_progress');
    try {
      await createEmbeddings();
    } catch (err) {
      console.error('Failed to start embedding creation:', err);
      setEmbeddingStatus('failed');
    }
  };

  const handleHistoryClick = (question: string) => {
    handleSendMessage(question);
  };

  return (
    <div className="app">
      <Sidebar
        history={history}
        onNewChat={handleNewChat}
        onClearHistory={handleClearHistory}
        onCreateEmbeddings={handleCreateEmbeddings}
        isCreatingEmbeddings={isCreatingEmbeddings}
        embeddingStatus={embeddingStatus}
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
              <ChatMessage 
                key={idx} 
                message={msg}
                previousQuestion={messages[idx - 1]?.content}
              />
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
