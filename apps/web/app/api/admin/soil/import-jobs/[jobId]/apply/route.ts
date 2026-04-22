import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../../../lib/server/auth.mjs';
import { startSoilImportApplyJob } from '../../../../../../../lib/server/soilImportJobRepository.mjs';

export async function POST(request: NextRequest, context: { params: Promise<{ jobId: string }> }) {
  try {
    await requireAdminRequestUser(request);
    const payload = await request.json();
    const params = await context.params;
    const result = await startSoilImportApplyJob({
      jobId: params.jobId,
      mode: payload.mode === 'replace' ? 'replace' : 'incremental',
      confirmFullReplace: Boolean(payload.confirm_full_replace),
    });
    return NextResponse.json(result, { status: 202 });
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '导入应用启动失败' }, { status: 400 });
  }
}
