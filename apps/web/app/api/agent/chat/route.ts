import crypto from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';

import { requireRequestUser } from '../../../../lib/server/auth.mjs';
import { buildAnalysisContext, buildRequestUnderstanding } from '../../../../lib/server/agentChatEvidence.mjs';

function mapMode(answerType: string, outputMode: string) {
  if (outputMode === 'advice_mode') return 'advice';
  if (outputMode === 'warning_mode') return 'data_query';
  if (answerType === 'guidance_answer') return 'analysis';
  if (answerType === 'fallback_answer') return 'analysis';
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

    const answerType = String(data.answer_type || '');
    const outputMode = String(data.output_mode || '');
    const guidanceReason = String(data.guidance_reason || '');
    const fallbackReason = String(data.fallback_reason || '');
    const toolTrace = Array.isArray(data.tool_trace) ? data.tool_trace : [];
    const queryLogEntries = Array.isArray(data.query_log_entries) ? data.query_log_entries : [];
    const answerFacts = data.answer_facts && typeof data.answer_facts === 'object' ? data.answer_facts : {};
    const queryResult = data.query_result && typeof data.query_result === 'object' ? data.query_result : {};

    const mode = mapMode(answerType, outputMode);
    const analysisContext = buildAnalysisContext({
      intent: data.intent,
      toolTrace,
      answerFacts,
      queryLogEntries,
    });
    const requestUnderstanding = buildRequestUnderstanding({
      question,
      intent: data.intent,
      inputType: data.input_type,
      toolTrace,
      queryLogEntries,
    });

    return NextResponse.json({
      answer: data.final_answer || '',
      mode,
      data: {
        session_id: data.session_id,
        turn_id: data.turn_id,
        intent: data.intent,
        answer_type: answerType,
        output_mode: outputMode,
        guidance_reason: guidanceReason,
        fallback_reason: fallbackReason,
        input_type: data.input_type,
        should_query: data.should_query,
        conversation_closed: Boolean(data.conversation_closed),
      },
      evidence: {
        response_meta: {
          confidence: data.should_query ? 'medium' : 'high',
          source_types: toolTrace.length > 0 ? ['database'] : ['guardrail'],
          fallback_reason: fallbackReason,
        },
        request_understanding: requestUnderstanding,
        analysis_context: analysisContext,
        tool_trace: toolTrace,
        answer_facts: answerFacts,
        query_result: queryResult,
        historical_query: {
          rule: answerType,
          sql: 'smart_agriculture.fact_soil_moisture',
          since: '',
        },
        execution_plan: [
          'request_understanding',
          toolTrace.length > 0 ? 'query_repository' : 'safe_guardrail',
          'answer_generation',
        ],
      },
      processing: {
        intent_recognition: '受限 Flow',
        data_query: toolTrace.length > 0 ? 'Python Agent / SoilRepository' : 'Boundary Guard',
        answer_generation: answerType || 'fallback_answer',
        ai_involvement: toolTrace.length > 0 ? '中' : '低',
        orchestration: 'Next BFF -> Python Agent',
        memory: requestUnderstanding.used_context ? '上下文继承' : '无',
      },
    });
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'chat request failed' }, { status: 502 });
  }
}
