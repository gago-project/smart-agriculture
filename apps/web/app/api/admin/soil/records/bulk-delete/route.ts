import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../../lib/server/auth.mjs';
import { removeSoilRecords } from '../../../../../../lib/server/soilAdminRepository.mjs';
import { isBackendProxyEnabled, proxyToBackend } from '../../../../../../lib/backendProxy.mjs';

export async function POST(request: NextRequest) {
  if (isBackendProxyEnabled()) return proxyToBackend(request, 'admin/soil/records/bulk-delete');
  try {
    await requireAdminRequestUser(request);
    const payload = await request.json();
    const ids = Array.isArray(payload.ids) ? payload.ids : [];
    const result = await removeSoilRecords(ids);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '批量删除失败' }, { status: 400 });
  }
}
