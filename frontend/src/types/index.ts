export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sql?: string;
  results?: Record<string, unknown>[];
  chart?: ChartConfig | null;
}

export interface ChatRequest {
  question: string;
  chat_history: ChatMessage[];
}

export interface ChatResponse {
  success: boolean;
  sql_query?: string;
  results?: Record<string, unknown>[];
  error?: string;
  message: string;
}

export interface QueryLog {
  timestamp: string;
  question: string;
  sql_query: string;
  success: boolean;
  error_message?: string;
}

export interface HistoryResponse {
  success: boolean;
  count: number;
  logs: QueryLog[];
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
