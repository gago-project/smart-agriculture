import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../../../lib/server/auth.mjs';
import { SoilImportPreviewCacheError } from '../../../../../../../lib/server/soilImportPreviewCache.mjs';
import { listSoilImportPreviewDiffPage } from '../../../../../../../lib/server/soilImportPreviewService.mjs';

export async function GET(request: NextRequest, context: { params: Promise<{ previewToken: string }> }) {
  try {
    await requireAdminRequestUser(request);
    const params = await context.params;
    const searchParams = request.nextUrl.searchParams;
    const result = await listSoilImportPreviewDiffPage(params.previewToken, {
      type: searchParams.get('type') || 'all',
      page: searchParams.get('page') || '1',
      page_size: '10',
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    if (error instanceof SoilImportPreviewCacheError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '导入 diff 查询失败' }, { status: 400 });
  }
}
