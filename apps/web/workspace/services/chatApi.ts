import type { ChatApiErrorPayload, ChatBlockResponse, ChatResponse, ChatTurnContext } from '../types/chat';
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

export async function fetchChatBlock(
  snapshotId: string,
  blockType: string,
  page: number,
  pageSize = 10,
): Promise<ChatBlockResponse> {
  const params = new URLSearchParams({
    snapshot_id: snapshotId,
    block_type: blockType,
    page: String(page),
    page_size: String(pageSize),
  });
  return await requestJson(`/api/agent/chat-block?${params.toString()}`, { method: 'GET' });
}

export async function sendChat(
  sessionId: string,
  turnId: number,
  clientMessageId: string,
  message: string,
  currentContext: ChatTurnContext,
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
        turn_id: turnId,
        client_message_id: clientMessageId,
        current_context: currentContext,
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
