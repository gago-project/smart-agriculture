import { NextResponse } from 'next/server';

export async function GET() {
  const agentBaseUrl = process.env.AGENT_BASE_URL || 'http://agent:8000';
  try {
    const response = await fetch(`${agentBaseUrl}/summary`, { cache: 'no-store' });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json({
      latest_time: '待连接',
      total_records: 0,
      risky_devices: 0,
      avg_water20cm: null,
      devices: [],
      detail: error instanceof Error ? error.message : 'unknown_error'
    }, { status: 200 });
  }
}
