import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireRequestUser } from '../../../../../lib/server/auth.mjs';
import { listRealConversationCases } from '../../../../../lib/server/realConversationLibrary.mjs';

const ALLOWED_USERNAME = 'gago-dev';

export async function GET(request: NextRequest) {
  try {
    const session = await requireRequestUser(request);
    if (!session) {
      throw new AuthRequestError('authentication required', 401);
    }
    if (session.user.username !== ALLOWED_USERNAME) {
      throw new AuthRequestError('permission denied', 403);
    }

    const cases = await listRealConversationCases();
    return NextResponse.json({
      total_count: cases.length,
      cases,
    });
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : '真实问答库加载失败' },
      { status: 400 },
    );
  }
}
