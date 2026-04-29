import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireRequestUser } from '../../../../lib/server/auth.mjs';
import { createChatSession, listChatSessions } from '../../../../lib/server/chatSessionRepository.mjs';

export async function GET(request: NextRequest) {
  try {
    const session = await requireRequestUser(request);
    if (!session) {
      throw new AuthRequestError('authentication required', 401);
    }
    const result = await listChatSessions({
      ownerUserId: session.user.id,
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : '会话列表加载失败' },
      { status: 400 },
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const session = await requireRequestUser(request);
    if (!session) {
      throw new AuthRequestError('authentication required', 401);
    }
    const payload = await request.json();
    const result = await createChatSession({
      ownerUserId: session.user.id,
      title: String(payload?.title || '').trim() || '新会话',
    });
    return NextResponse.json(result, { status: 201 });
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : '会话创建失败' },
      { status: 400 },
    );
  }
}
