import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../lib/server/auth.mjs';
import { SoilImportPreviewCacheError } from '../../../../../lib/server/soilImportPreviewCache.mjs';
import { createSoilImportPreview } from '../../../../../lib/server/soilImportPreviewService.mjs';

export async function POST(request: NextRequest) {
  try {
    await requireAdminRequestUser(request);
    const payload = await request.json();
    const result = await createSoilImportPreview({
      filename: String(payload.filename || 'soil.xlsx'),
      contentBase64: String(payload.content_base64 || ''),
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    if (error instanceof SoilImportPreviewCacheError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '导入预览创建失败' }, { status: 400 });
  }
}
