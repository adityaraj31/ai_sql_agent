export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sql?: string;
  results?: Record<string, unknown>[];
  chart?: ChartConfig | null;
  is_relevant?: boolean;
}

export interface ChatRequest {
  question: string;
  session_id?: string;
  chat_history: ChatMessage[];
}

export interface ChatResponse {
  success: boolean;
  session_id?: string;
  sql_query?: string;
  results?: Record<string, unknown>[];
  error?: string;
  message: string;
  is_relevant?: boolean;
}

export interface ChatSession {
  session_id: string;
  title: string | null;
  created_at: string;
  message_count: number;
}

export interface HistoryResponse {
  success: boolean;
  count: number;
  logs: ChatSession[];
}

export interface SessionMessagesResponse {
  success: boolean;
  session_id: string;
  messages: ChatMessage[];
}

export interface QueryLog {
  session_id: string;
  title: string | null;
  created_at: string;
  message_count: number;
  question?: string;
  success?: boolean;
}

export interface EmbeddingsResponse {
  success: boolean;
  message: string;
}

export interface ChartConfig {
  chart_type: 'bar' | 'line' | 'pie' | 'scatter' | 'none';
  x_axis: string;
  y_axis: string;
  title: string;
}
