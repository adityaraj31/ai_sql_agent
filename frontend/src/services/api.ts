import axios from 'axios';
import type { ChatRequest, ChatResponse, HistoryResponse, EmbeddingsResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

export const chat = async (request: ChatRequest): Promise<ChatResponse> => {
  const response = await api.post<ChatResponse>('/chat', request);
  return response.data;
};

export const getHistory = async (): Promise<HistoryResponse> => {
  const response = await api.get<HistoryResponse>('/history');
  return response.data;
};

export const clearHistory = async (): Promise<{ success: boolean; message: string }> => {
  const response = await api.delete<{ success: boolean; message: string }>('/history');
  return response.data;
};

export const createEmbeddings = async (): Promise<EmbeddingsResponse> => {
  const response = await api.post<EmbeddingsResponse>('/embeddings');
  return response.data;
};

export const getEmbeddingStatus = async (): Promise<{ status: string; message: string }> => {
  const response = await api.get<{ status: string; message: string }>('/embeddings/status');
  return response.data;
};

export const healthCheck = async (): Promise<{ status: string; service: string; version: string }> => {
  const response = await api.get('/health');
  return response.data;
};
