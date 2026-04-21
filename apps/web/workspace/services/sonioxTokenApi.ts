import { useAuthStore } from '../store/authStore';

export interface SonioxTemporaryToken {
  api_key: string;
  expires_at: string;
  websocket_url: string;
  model: string;
}

function extractError(payload: unknown): string {
  if (payload && typeof payload === 'object' && 'error' in payload) {
    const error = (payload as { error?: string }).error;
    if (error) return error;
  }
  return '语音服务暂时不可用，请稍后重试';
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

export async function fetchSonioxTemporaryToken(): Promise<SonioxTemporaryToken> {
  const token = useAuthStore.getState().token;
  const response = await fetch('/api/soniox/token', {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  });
  const payload = await parseJson(response);

  if (!response.ok) {
    if (response.status === 401) {
      useAuthStore.getState().clearSession();
      throw new Error('登录已失效，请重新登录');
    }
    throw new Error(extractError(payload));
  }

  if (!payload || typeof payload !== 'object') {
    throw new Error('响应格式不正确');
  }

  const parsed = payload as Record<string, unknown>;
  if (
    typeof parsed.api_key !== 'string' ||
    typeof parsed.websocket_url !== 'string' ||
    typeof parsed.model !== 'string'
  ) {
    throw new Error('响应格式不正确');
  }

  return {
    api_key: parsed.api_key,
    expires_at: typeof parsed.expires_at === 'string' ? parsed.expires_at : '',
    websocket_url: parsed.websocket_url,
    model: parsed.model
  };
}
