import { useAuthStore } from '../store/authStore';

export interface RealConversationCase {
  id: number;
  category: string;
  question: string;
  turns: string[];
  capability: string;
  expectation: string;
}

interface RealConversationLibraryPayload {
  total_count?: number;
  cases?: RealConversationCase[];
  error?: string;
}

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function extractError(payload: RealConversationLibraryPayload): string {
  return payload.error || '真实问答库加载失败';
}

export async function fetchRealConversationLibrary(): Promise<{
  totalCount: number;
  cases: RealConversationCase[];
}> {
  const response = await fetch('/api/developer/soil/real-conversation-library', {
    method: 'GET',
    headers: authHeaders(),
    cache: 'no-store',
  });
  const payload = (await response.json()) as RealConversationLibraryPayload;

  if (!response.ok) {
    if (response.status === 401) {
      useAuthStore.getState().clearSession();
      throw new Error('登录已失效，请重新登录');
    }
    throw new Error(extractError(payload));
  }

  return {
    totalCount: Number(payload.total_count || 0),
    cases: Array.isArray(payload.cases) ? payload.cases : [],
  };
}
