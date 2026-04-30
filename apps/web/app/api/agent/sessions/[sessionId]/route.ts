import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireRequestUser } from '../../../../../lib/server/auth.mjs';
import { getChatSessionDetail, renameChatSession } from '../../../../../lib/server/chatSessionRepository.mjs';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ sessionId: string }> },
) {
  try {
    const session = await requireRequestUser(request);
    if (!session) {
      throw new AuthRequestError('authentication required', 401);
    }
    const params = await context.params;
    const { sessionId } = params;
    const result = await getChatSessionDetail({
      ownerUserId: session.user.id,
      sessionId,
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : '会话详情加载失败' },
      { status: 400 },
    );
  }
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ sessionId: string }> },
) {
  try {
    const session = await requireRequestUser(request);
    if (!session) {
      throw new AuthRequestError('authentication required', 401);
    }
    const payload = await request.json();
    if (typeof payload?.title !== 'string') {
      throw new Error('title is required');
    }
    const params = await context.params;
    const result = await renameChatSession({
      ownerUserId: session.user.id,
      sessionId: params.sessionId,
      title: payload.title,
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : '会话名称更新失败' },
      { status: 400 },
    );
  }
}
