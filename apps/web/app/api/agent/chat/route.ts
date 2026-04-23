import crypto from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';

import { requireRequestUser } from '../../../../lib/server/auth.mjs';

function mapMode(answerType: string) {
  if (answerType === 'closing_answer') return 'analysis';
  if (answerType.includes('closing')) return 'analysis';
  if (answerType.includes('advice')) return 'advice';
  if (answerType.includes('clarification')) return 'analysis';
  if (answerType.includes('safe') || answerType.includes('boundary') || answerType.includes('fallback')) return 'analysis';
  return 'data_query';
}

export async function POST(request: NextRequest) {
  const session = await requireRequestUser(request);
  if (!session) {
    return NextResponse.json({ error: 'authentication required' }, { status: 401 });
  }

  const payload = await request.json();
  const agentBaseUrl = process.env.AGENT_BASE_URL || 'http://agent:8000';
  const question = String(payload.question || '').trim();
  const history = Array.isArray(payload.history) ? payload.history : [];
  const threadId = String(payload.thread_id || '').trim() || crypto.randomUUID();

  if (!question) {
    return NextResponse.json({ error: 'question is required' }, { status: 400 });
  }

  try {
    const response = await fetch(`${agentBaseUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: question,
        session_id: threadId,
        turn_id: history.length + 1,
      }),
      cache: 'no-store',
    });
    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json({ error: data?.detail || data?.error || 'agent request failed' }, { status: response.status });
    }

    const mode = mapMode(String(data.answer_type || ''));
    const contextMeta = data.context_used && typeof data.context_used === 'object' ? data.context_used : {};
    const inheritanceMode = String(contextMeta.inheritance_mode || '');
    const usedContext =
      ['carry_frame', 'convert_frame'].includes(inheritanceMode)
      || (Array.isArray(contextMeta.inherited_fields) && contextMeta.inherited_fields.length > 0);
    return NextResponse.json({
      answer: data.final_answer || '',
      mode,
      data: {
        session_id: data.session_id,
        turn_id: data.turn_id,
        intent: data.intent,
        answer_type: data.answer_type,
        input_type: data.input_type,
        should_query: data.should_query,
        conversation_closed: Boolean(data.conversation_closed),
        context_used: contextMeta,
      },
      evidence: {
        response_meta: {
          confidence: data.should_query ? 'medium' : 'high',
          source_types: data.should_query ? ['database', 'rule'] : ['guardrail'],
          fallback_reason: data.should_query ? '' : 'safe_or_boundary',
        },
        request_understanding: {
          original_question: question,
          normalized_question: question,
          resolved_question: question,
          domain: 'soil',
          task_type: data.intent,
          understanding_engine: 'restricted-flow',
          used_context: usedContext,
          ignored_phrases: data.input_type === 'meaningless_input' ? [question] : [],
          window: { window_type: 'all', window_value: null },
          future_window: null,
        },
        analysis_context: {
          domain: 'soil',
          region_name: '',
          region_level: 'county',
          query_type: data.intent,
        },
        historical_query: {
          rule: data.answer_type,
          sql: 'smart_agriculture.fact_soil_moisture',
          since: '',
        },
        execution_plan: [
          'request_understanding',
          data.should_query ? 'query_repository' : 'safe_guardrail',
          'answer_generation',
        ],
      },
      processing: {
        intent_recognition: '受限 Flow',
        data_query: data.should_query ? 'Python Agent / SoilRepository' : 'Boundary Guard',
        answer_generation: data.answer_type || 'fallback_answer',
        ai_involvement: data.should_query ? '中' : '低',
        orchestration: 'Next BFF -> Python Agent',
        memory: usedContext ? `使用多轮上下文：${inheritanceMode || 'context'}` : '无',
      },
    });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'chat request failed' }, { status: 502 });
  }
}
