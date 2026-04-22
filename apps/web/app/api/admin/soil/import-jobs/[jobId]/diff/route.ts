import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../../../lib/server/auth.mjs';
import { listSoilImportJobDiff } from '../../../../../../../lib/server/soilImportJobRepository.mjs';

export async function GET(request: NextRequest, context: { params: Promise<{ jobId: string }> }) {
  try {
    await requireAdminRequestUser(request);
    const params = await context.params;
    const searchParams = request.nextUrl.searchParams;
    const result = await listSoilImportJobDiff(params.jobId, {
      type: searchParams.get('type') || 'all',
      page: searchParams.get('page') || '1',
      page_size: searchParams.get('page_size') || '20',
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '导入 diff 查询失败' }, { status: 400 });
  }
}
