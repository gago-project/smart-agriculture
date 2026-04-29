import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireRequestUser } from '../../../../lib/server/auth.mjs';
import { getChatBlockPage } from '../../../../lib/server/chatSessionRepository.mjs';

export async function GET(request: NextRequest) {
  try {
    const session = await requireRequestUser(request);
    if (!session) {
      throw new AuthRequestError('authentication required', 401);
    }
    const sessionId = request.nextUrl.searchParams.get('session_id') || '';
    const turnId = Number(request.nextUrl.searchParams.get('turn_id') || '0');
    const blockId = request.nextUrl.searchParams.get('block_id') || '';
    const page = Number(request.nextUrl.searchParams.get('page') || '1');
    const result = await getChatBlockPage({
      ownerUserId: session.user.id,
      sessionId,
      turnId,
      blockId,
      page,
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : '区块数据加载失败' },
      { status: 400 },
    );
  }
}
