import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../../lib/server/auth.mjs';
import { getSoilImportJob } from '../../../../../../lib/server/soilImportJobRepository.mjs';

export async function GET(request: NextRequest, context: { params: Promise<{ jobId: string }> }) {
  try {
    await requireAdminRequestUser(request);
    const params = await context.params;
    const result = await getSoilImportJob(params.jobId);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '导入任务查询失败' }, { status: 400 });
  }
}
