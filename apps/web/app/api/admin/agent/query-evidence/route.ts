import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../lib/server/auth.mjs';
import { getAgentQueryEvidenceByTurn } from '../../../../../lib/server/agentLogRepository.mjs';

export async function GET(request: NextRequest) {
  try {
    await requireAdminRequestUser(request);
    const sessionId = request.nextUrl.searchParams.get('session_id') || '';
    const turnId = request.nextUrl.searchParams.get('turn_id') || '';
    const result = await getAgentQueryEvidenceByTurn({
      session_id: sessionId,
      turn_id: turnId,
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : '查询证据加载失败' },
      { status: 400 },
    );
  }
}
