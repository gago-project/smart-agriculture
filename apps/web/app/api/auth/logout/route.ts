import { NextRequest, NextResponse } from 'next/server';

import { logoutWithToken, requireRequestUser } from '../../../../lib/server/auth.mjs';

export async function POST(request: NextRequest) {
  const session = await requireRequestUser(request);
  if (!session) {
    return NextResponse.json({ error: 'authentication required' }, { status: 401 });
  }
  await logoutWithToken(session.token);
  return NextResponse.json({ ok: true });
}
