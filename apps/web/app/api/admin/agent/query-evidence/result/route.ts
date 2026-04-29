import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../../lib/server/auth.mjs';
import { getAgentQueryEvidenceResultByQueryId } from '../../../../../../lib/server/agentLogRepository.mjs';

export async function GET(request: NextRequest) {
  try {
    await requireAdminRequestUser(request);
    const queryId = request.nextUrl.searchParams.get('query_id') || '';
    const result = await getAgentQueryEvidenceResultByQueryId(queryId);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : '查询证据结果加载失败' },
      { status: 400 },
    );
  }
}
