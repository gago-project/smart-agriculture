import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../../lib/server/auth.mjs';
import { removeSoilRecords } from '../../../../../../lib/server/soilAdminRepository.mjs';

export async function POST(request: NextRequest) {
  try {
    await requireAdminRequestUser(request);
    const payload = await request.json();
    const recordIds = Array.isArray(payload.record_ids) ? payload.record_ids : [];
    const result = await removeSoilRecords(recordIds);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '批量删除失败' }, { status: 400 });
  }
}
