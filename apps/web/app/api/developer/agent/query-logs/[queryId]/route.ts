import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireRoleRequestUser } from '../../../../../../lib/server/auth.mjs';
import { getAgentQueryLogDetail } from '../../../../../../lib/server/agentLogRepository.mjs';

export async function GET(request: NextRequest, context: { params: Promise<{ queryId: string }> }) {
  try {
    await requireRoleRequestUser(request, ['admin', 'developer']);
    const params = await context.params;
    const result = await getAgentQueryLogDetail(params.queryId);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '查询日志详情加载失败' }, { status: 400 });
  }
}
