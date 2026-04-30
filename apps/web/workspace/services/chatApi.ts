import type {
  ChatApiErrorPayload,
  ChatBlockResponse,
  ChatResponse,
  ChatSessionDetailResponse,
  ChatSessionListResponse,
} from '../types/chat';
import { useAuthStore } from '../store/authStore';

const DEFAULT_TIMEOUT_MS = 30000;

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function extractError(payload: unknown): string {
  if (payload && typeof payload === 'object' && 'error' in payload) {
    const candidate = (payload as ChatApiErrorPayload).error;
    if (candidate) {
      return candidate;
    }
  }
  return '请求失败，请稍后重试';
}

async function parseJson(response: Response): Promise<unknown> {
  try {
    return (await response.json()) as unknown;
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new Error('响应格式不正确');
    }
    throw error;
  }
}

async function requestJson<T>(input: string, init: RequestInit): Promise<T> {
  const response = await fetch(input, {
    ...init,
    headers: {
      ...authHeaders(),
      ...(init.headers || {}),
    },
    cache: 'no-store',
  });
  const payload = await parseJson(response);
  if (!response.ok) {
    if (response.status === 401) {
      useAuthStore.getState().clearSession();
      throw new Error('登录已失效，请重新登录');
    }
    throw new Error(extractError(payload));
  }
  return payload as T;
}

export async function createChatSession(title = '新会话'): Promise<{ session_id: string; title: string }> {
  return await requestJson('/api/agent/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
}

export async function fetchChatSessions(): Promise<ChatSessionListResponse> {
  return await requestJson('/api/agent/sessions', { method: 'GET' });
}

export async function fetchChatSession(sessionId: string): Promise<ChatSessionDetailResponse> {
  return await requestJson(`/api/agent/sessions/${encodeURIComponent(sessionId)}`, { method: 'GET' });
}

export async function renameChatSession(sessionId: string, title: string): Promise<{ session_id: string; title: string }> {
  return await requestJson(`/api/agent/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
}

export async function archiveChatSession(sessionId: string): Promise<{ session_id: string; archived: boolean }> {
  return await requestJson(`/api/agent/sessions/${encodeURIComponent(sessionId)}/archive`, { method: 'POST' });
}

export async function fetchChatBlock(
  sessionId: string,
  turnId: number,
  blockId: string,
  page: number,
): Promise<ChatBlockResponse> {
  const params = new URLSearchParams({
    session_id: sessionId,
    turn_id: String(turnId),
    block_id: blockId,
    page: String(page),
  });
  return await requestJson(`/api/agent/chat-block?${params.toString()}`, { method: 'GET' });
}

export async function sendChat(
  sessionId: string,
  clientMessageId: string,
  message: string,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<ChatResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await requestJson('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        client_message_id: clientMessageId,
        message,
        timezone: 'Asia/Shanghai',
      }),
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('请求超时，请稍后重试');
    }
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('未知错误');
  } finally {
    clearTimeout(timer);
  }
}
