import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireRoleRequestUser } from '../../../../../lib/server/auth.mjs';
import { listAgentQueryLogs } from '../../../../../lib/server/agentLogRepository.mjs';

export async function GET(request: NextRequest) {
  try {
    await requireRoleRequestUser(request, ['admin', 'developer']);
    const searchParams = request.nextUrl.searchParams;
    const result = await listAgentQueryLogs({
      page: searchParams.get('page') || '1',
      page_size: searchParams.get('page_size') || '30',
      keyword: searchParams.get('keyword') || '',
      session_id: searchParams.get('session_id') || '',
      query_type: searchParams.get('query_type') || '',
      intent: searchParams.get('intent') || '',
      status: searchParams.get('status') || '',
      created_at_from: searchParams.get('created_at_from') || '',
      created_at_to: searchParams.get('created_at_to') || '',
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '查询日志加载失败' }, { status: 400 });
  }
}
