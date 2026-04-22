import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../lib/server/auth.mjs';
import { createSoilImportJob } from '../../../../../lib/server/soilImportJobRepository.mjs';

export async function POST(request: NextRequest) {
  try {
    const session = await requireAdminRequestUser(request);
    const payload = await request.json();
    const result = await createSoilImportJob({
      filename: String(payload.filename || 'soil.xlsx'),
      contentBase64: String(payload.content_base64 || ''),
      operatorUser: session.user,
    });
    return NextResponse.json(result, { status: 202 });
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '导入预览创建失败' }, { status: 400 });
  }
}
