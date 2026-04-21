import { NextRequest, NextResponse } from 'next/server';

import { loginWithPassword } from '../../../../lib/server/auth.mjs';

export async function POST(request: NextRequest) {
  const payload = await request.json();
  try {
    const session = await loginWithPassword(String(payload.username || '').trim(), String(payload.password || '').trim());
    return NextResponse.json(session);
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : '登录失败' }, { status: 401 });
  }
}
