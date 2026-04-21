export type ChatMode = 'data_query' | 'advice' | 'analysis' | 'unknown';
export type MessageRole = 'user' | 'assistant';
export type MessageStatus = 'pending' | 'streaming' | 'done' | 'error';

export interface ChatHistoryTurn {
  role: MessageRole;
  content: string;
}

export interface ProcessingTrace {
  intent_recognition: string;
  data_query: string;
  answer_generation: string;
  ai_involvement: string;
  orchestration?: string;
  memory?: string;
}

export interface MessageMeta {
  mode?: ChatMode | string;
  data?: unknown;
  evidence?: unknown;
  processing?: ProcessingTrace | null;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  status: MessageStatus;
  createdAt: number;
  meta?: MessageMeta;
}

export interface Session {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
}

export interface ChatResponse {
  answer: string;
  mode: ChatMode | string;
  data: unknown;
  evidence: unknown;
  processing?: ProcessingTrace | null;
}

export interface ChatApiErrorPayload {
  error?: string;
}
