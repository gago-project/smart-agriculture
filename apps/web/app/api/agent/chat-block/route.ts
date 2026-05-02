import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireRequestUser } from '../../../../lib/server/auth.mjs';
import { getChatBlockPageBySnapshot } from '../../../../lib/server/chatBlockRepository.mjs';

export async function GET(request: NextRequest) {
  try {
    const session = await requireRequestUser(request);
    if (!session) {
      throw new AuthRequestError('authentication required', 401);
    }
    const snapshotId = request.nextUrl.searchParams.get('snapshot_id') || '';
    const blockType = request.nextUrl.searchParams.get('block_type') || '';
    const page = Number(request.nextUrl.searchParams.get('page') || '1');
    const pageSize = Number(request.nextUrl.searchParams.get('page_size') || '10');
    const result = await getChatBlockPageBySnapshot({
      snapshotId,
      blockType,
      page,
      pageSize,
    });
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json(
      { error: error instanceof Error ? error.message : '区块数据加载失败' },
      { status: 400 },
    );
  }
}
