import { NextRequest, NextResponse } from 'next/server';

import { requireRequestUser } from '../../../../lib/server/auth.mjs';

export async function GET(request: NextRequest) {
  const session = await requireRequestUser(request);
  if (!session) {
    return NextResponse.json({ error: 'authentication required' }, { status: 401 });
  }
  return NextResponse.json({ user: session.user });
}
