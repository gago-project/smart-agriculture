import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../lib/server/auth.mjs';
import { importSoilWorkbook } from '../../../../../lib/server/soilAdminRepository.mjs';
import { isBackendProxyEnabled, proxyToBackend } from '../../../../../lib/backendProxy.mjs';

export async function POST(request: NextRequest) {
  if (isBackendProxyEnabled()) return proxyToBackend(request, 'admin/soil/upload');
  try {
    await requireAdminRequestUser(request);
    const payload = await request.json();
    const result = await importSoilWorkbook({
      filename: payload.filename,
      contentBase64: payload.content_base64,
      mode: payload.mode === 'replace' ? 'replace' : 'incremental',
      confirmFullReplace: Boolean(payload.confirm_full_replace),
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Excel 导入失败' }, { status: 400 });
  }
}
