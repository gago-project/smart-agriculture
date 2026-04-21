export interface AuthUser {
  id: number;
  username: string;
  role?: string;
}

interface LoginResponsePayload {
  token?: string;
  user?: AuthUser;
  expires_at?: string;
  error?: string;
}

interface MeResponsePayload {
  user?: AuthUser;
  error?: string;
}

function extractError(payload: unknown): string {
  if (payload && typeof payload === 'object' && 'error' in payload) {
    const error = (payload as { error?: string }).error;
    if (error) return error;
  }
  return '认证请求失败，请稍后重试';
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

export async function login(username: string, password: string): Promise<{
  token: string;
  user: AuthUser;
  expiresAt: string;
}> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  const payload = (await parseJson(response)) as LoginResponsePayload;
  if (!response.ok) {
    throw new Error(extractError(payload));
  }
  if (!payload.token || !payload.user || !payload.expires_at) {
    throw new Error('响应格式不正确');
  }
  return {
    token: payload.token,
    user: payload.user,
    expiresAt: payload.expires_at
  };
}

export async function fetchCurrentUser(token: string): Promise<AuthUser> {
  const response = await fetch('/api/auth/me', {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  const payload = (await parseJson(response)) as MeResponsePayload;
  if (!response.ok) {
    throw new Error(extractError(payload));
  }
  if (!payload.user) {
    throw new Error('响应格式不正确');
  }
  return payload.user;
}

export async function logout(token: string): Promise<void> {
  const response = await fetch('/api/auth/logout', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
  const payload = await parseJson(response);
  if (!response.ok) {
    throw new Error(extractError(payload));
  }
}
