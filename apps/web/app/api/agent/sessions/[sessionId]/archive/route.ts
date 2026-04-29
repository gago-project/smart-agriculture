import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireRequestUser } from '../../../../../../lib/server/auth.mjs';
import { archiveChatSession } from '../../../../../../lib/server/chatSessionRepository.mjs';

export async function POST(
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
    const result = await archiveChatSession({
      ownerUserId: session.user.id,
      sessionId,
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : '会话归档失败' },
      { status: 400 },
    );
  }
}
