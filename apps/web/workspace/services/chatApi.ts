import type { ChatResponse, ChatApiErrorPayload, ChatHistoryTurn } from '../types/chat';
import { useAuthStore } from '../store/authStore';

const DEFAULT_TIMEOUT_MS = 30000;

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

export async function sendChat(
  question: string,
  history: ChatHistoryTurn[] = [],
  threadId?: string,
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<ChatResponse> {
  const token = useAuthStore.getState().token;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({ question, history, thread_id: threadId }),
      signal: controller.signal
    });

    const json = await parseJson(response);

    if (!response.ok) {
      if (response.status === 401) {
        useAuthStore.getState().clearSession();
        throw new Error('登录已失效，请重新登录');
      }
      throw new Error(extractError(json));
    }

    if (!json || typeof json !== 'object') {
      throw new Error('响应格式不正确');
    }

    const parsed = json as Partial<ChatResponse>;
    return {
      answer: typeof parsed.answer === 'string' ? parsed.answer : '',
      mode: typeof parsed.mode === 'string' ? parsed.mode : 'unknown',
      data: parsed.data ?? null,
      evidence: parsed.evidence ?? null,
      processing:
        parsed.processing && typeof parsed.processing === 'object'
          ? parsed.processing
          : null
    };
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
