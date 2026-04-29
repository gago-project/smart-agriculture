import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireRequestUser } from '../../../../lib/server/auth.mjs';
import { executeChatTurn } from '../../../../lib/server/chatSessionRepository.mjs';

export async function POST(request: NextRequest) {
  try {
    const session = await requireRequestUser(request);
    if (!session) {
      throw new AuthRequestError('authentication required', 401);
    }

    const payload = await request.json();
    const sessionId = String(payload?.session_id || '').trim();
    const clientMessageId = String(payload?.client_message_id || '').trim();
    const message = String(payload?.message || '').trim();
    const timezone = String(payload?.timezone || 'Asia/Shanghai').trim() || 'Asia/Shanghai';
    const agentBaseUrl = process.env.AGENT_BASE_URL || 'http://agent:8000';

    if (!sessionId) {
      return NextResponse.json({ error: 'session_id is required' }, { status: 400 });
    }
    if (!clientMessageId) {
      return NextResponse.json({ error: 'client_message_id is required' }, { status: 400 });
    }
    if (!message) {
      return NextResponse.json({ error: 'message is required' }, { status: 400 });
    }

    const result = await executeChatTurn({
      ownerUserId: session.user.id,
      sessionId,
      clientMessageId,
      message,
      timezone,
      agentBaseUrl,
    });

    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'chat request failed' },
      { status: 400 },
    );
  }
}
