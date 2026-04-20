import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const payload = await request.json();
  const agentBaseUrl = process.env.AGENT_BASE_URL || 'http://agent:8000';

  try {
    const response = await fetch(`${agentBaseUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      cache: 'no-store'
    });
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return NextResponse.json({
      intent: 'clarification_needed',
      answer_type: 'fallback_answer',
      final_answer: '智能体服务暂时不可用，请稍后重试。',
      detail: error instanceof Error ? error.message : 'unknown_error'
    }, { status: 502 });
  }
}
