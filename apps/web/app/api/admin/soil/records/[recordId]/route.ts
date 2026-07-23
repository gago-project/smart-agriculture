import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../../lib/server/auth.mjs';
import { patchSoilRecord, removeSoilRecords } from '../../../../../../lib/server/soilAdminRepository.mjs';
import { isBackendProxyEnabled, proxyToBackend } from '../../../../../../lib/backendProxy.mjs';

export async function PATCH(request: NextRequest, context: { params: Promise<{ recordId: string }> }) {
  if (isBackendProxyEnabled()) {
    const { recordId } = await context.params;
    return proxyToBackend(request, `admin/soil/records/${encodeURIComponent(recordId)}`);
  }
  try {
    await requireAdminRequestUser(request);
    const payload = await request.json();
    const params = await context.params;
    const result = await patchSoilRecord(params.recordId, payload.field, payload.value);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '记录修改失败' }, { status: 400 });
  }
}

export async function DELETE(request: NextRequest, context: { params: Promise<{ recordId: string }> }) {
  if (isBackendProxyEnabled()) {
    const { recordId } = await context.params;
    return proxyToBackend(request, `admin/soil/records/${encodeURIComponent(recordId)}`);
  }
  try {
    await requireAdminRequestUser(request);
    const params = await context.params;
    const result = await removeSoilRecords([params.recordId]);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '记录删除失败' }, { status: 400 });
  }
}
