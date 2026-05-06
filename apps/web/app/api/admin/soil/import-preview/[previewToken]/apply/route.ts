import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../../../lib/server/auth.mjs';
import { SoilImportPreviewCacheError } from '../../../../../../../lib/server/soilImportPreviewCache.mjs';
import { applySoilImportPreview } from '../../../../../../../lib/server/soilImportPreviewService.mjs';

export async function POST(request: NextRequest, context: { params: Promise<{ previewToken: string }> }) {
  try {
    await requireAdminRequestUser(request);
    const payload = await request.json();
    const params = await context.params;
    const result = await applySoilImportPreview({
      previewToken: params.previewToken,
      mode: payload.mode === 'replace' ? 'replace' : 'incremental',
      confirmFullReplace: Boolean(payload.confirm_full_replace),
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    if (error instanceof SoilImportPreviewCacheError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '导入应用失败' }, { status: 400 });
  }
}
