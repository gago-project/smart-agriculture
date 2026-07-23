import { NextRequest, NextResponse } from 'next/server';

import { loginWithPassword } from '../../../../lib/server/auth.mjs';
import { fetchBackendJson, isBackendProxyEnabled } from '../../../../lib/backendProxy.mjs';

export async function POST(request: NextRequest) {
  if (isBackendProxyEnabled()) {
    // Forward credentials to the backend. This web app is cookie-less: the
    // client stores the returned token in localStorage and sends it as a
    // Bearer header, so there is no cookie to set here — we just reshape the
    // backend payload ({ token, expiresAt, user }) into the web contract
    // ({ token, expires_at, user }) the client already expects.
    const raw = await request.text();
    const { ok, status, data } = await fetchBackendJson(request, '/auth/login', {
      method: 'POST',
      body: raw,
      headers: { 'content-type': 'application/json' },
    });
    if (!ok) {
      const message =
        (data && typeof data === 'object' && (data.error || data.message)) || '登录失败';
      const normalized = Array.isArray(message) ? message.join('; ') : String(message);
      return NextResponse.json({ error: normalized }, { status: status || 401 });
    }
    const session = (data && typeof data === 'object' ? data : {}) as {
      token?: unknown;
      expiresAt?: unknown;
      expires_at?: unknown;
      user?: unknown;
    };
    return NextResponse.json({
      token: session.token,
      expires_at: session.expires_at ?? session.expiresAt,
      user: session.user,
    });
  }

  const payload = await request.json();
  try {
    const session = await loginWithPassword(String(payload.username || '').trim(), String(payload.password || '').trim());
    return NextResponse.json(session);
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : '登录失败' }, { status: 401 });
  }
}
