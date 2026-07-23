import { NextRequest, NextResponse } from 'next/server';

import { logoutWithToken, requireRequestUser } from '../../../../lib/server/auth.mjs';
import { fetchBackendJson, isBackendProxyEnabled } from '../../../../lib/backendProxy.mjs';

export async function POST(request: NextRequest) {
  if (isBackendProxyEnabled()) {
    // Forward the Bearer token so the backend invalidates the session. This app
    // is cookie-less (client clears its localStorage token itself), so there is
    // no cookie to clear here. Preserve the { ok: true } / 401 contract.
    const { ok, status, data } = await fetchBackendJson(request, '/auth/logout', {
      method: 'POST',
      body: null,
    });
    if (!ok) {
      return NextResponse.json({ error: 'authentication required' }, { status: status || 401 });
    }
    return NextResponse.json(
      data && typeof data === 'object' && 'ok' in data ? data : { ok: true },
    );
  }

  const session = await requireRequestUser(request);
  if (!session) {
    return NextResponse.json({ error: 'authentication required' }, { status: 401 });
  }
  await logoutWithToken(session.token);
  return NextResponse.json({ ok: true });
}
