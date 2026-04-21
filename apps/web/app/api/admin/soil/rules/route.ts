import { NextRequest, NextResponse } from 'next/server';

import { AuthRequestError, requireAdminRequestUser } from '../../../../../lib/server/auth.mjs';
import { listRuleConfig, patchRuleConfig } from '../../../../../lib/server/soilAdminRepository.mjs';

export async function GET(request: NextRequest) {
  try {
    await requireAdminRequestUser(request);
    const result = await listRuleConfig();
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '规则配置查询失败' }, { status: 400 });
  }
}

export async function PATCH(request: NextRequest) {
  try {
    await requireAdminRequestUser(request);
    const payload = await request.json();
    const result = await patchRuleConfig(payload);
    return NextResponse.json(result);
  } catch (error) {
    if (error instanceof AuthRequestError) {
      return NextResponse.json({ error: error.message }, { status: error.status });
    }
    return NextResponse.json({ error: error instanceof Error ? error.message : '规则配置更新失败' }, { status: 400 });
  }
}
