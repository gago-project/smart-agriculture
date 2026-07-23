import { NextRequest, NextResponse } from 'next/server';

import { requireRequestUser } from '../../../../lib/server/auth.mjs';
import { fetchBackendJson, isBackendProxyEnabled } from '../../../../lib/backendProxy.mjs';

export async function GET(request: NextRequest) {
  if (isBackendProxyEnabled()) {
    // Incoming GET carries the token in the Authorization header. The backend
    // exposes validation as POST /auth/validate (Bearer header honoured), so we
    // switch the method and let fetchBackendJson forward the Authorization
    // header. Return the backend's { user } as-is (matches web /auth/me shape).
    const { ok, status, data } = await fetchBackendJson(request, '/auth/validate', {
      method: 'POST',
      body: null,
    });
    if (!ok) {
      return NextResponse.json({ error: 'authentication required' }, { status: status || 401 });
    }
    const user = data && typeof data === 'object' ? (data as { user?: unknown }).user : undefined;
    return NextResponse.json({ user });
  }

  const session = await requireRequestUser(request);
  if (!session) {
    return NextResponse.json({ error: 'authentication required' }, { status: 401 });
  }
  return NextResponse.json({ user: session.user });
}
