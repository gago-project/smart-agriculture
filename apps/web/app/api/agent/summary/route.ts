import { NextRequest, NextResponse } from 'next/server';

import { requireRequestUser } from '../../../../lib/server/auth.mjs';

export async function GET(request: NextRequest) {
  const session = await requireRequestUser(request);
  if (!session) {
    return NextResponse.json({ error: 'authentication required' }, { status: 401 });
  }

  const agentBaseUrl = process.env.AGENT_BASE_URL || 'http://agent:8000';
  try {
    const response = await fetch(`${agentBaseUrl}/debug/summary`, { cache: 'no-store' });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json({
      error: 'agent summary request failed',
      detail: error instanceof Error ? error.message : 'unknown_error'
    }, { status: 502 });
  }
}
