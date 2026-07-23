import { withMysqlConnection } from './mysql.mjs';
import { sanitizeExecutedResult } from './soilResultSanitizer.mjs';

function parseJsonValue(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  if (typeof value === 'string') {
    try {
      return JSON.parse(value);
    } catch {
      return value;
    }
  }
  return value;
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function jsonStringify(value, fallback) {
  try {
    return JSON.stringify(value ?? fallback);
  } catch {
    return JSON.stringify(fallback);
  }
}

async function insertQueryLogs(entries) {
  const rows = asArray(entries)
    .filter((entry) => entry && typeof entry === 'object' && entry.query_id)
    .map((entry) => ({
      ...entry,
      executed_result_json: sanitizeExecutedResult(entry.executed_result_json, { queryType: entry.query_type }),
      result_digest_json: sanitizeExecutedResult(entry.result_digest_json, { queryType: entry.query_type }),
    }));
  if (rows.length === 0) {
    return;
  }

  await withMysqlConnection(async (connection) => {
    const sql = `INSERT INTO agent_query_log (
        query_id,
        session_id,
        turn_id,
        request_text,
        response_text,
        input_type,
        intent,
        answer_type,
        final_status,
        query_type,
        query_plan_json,
        query_spec_json,
        sql_fingerprint,
        executed_sql_text,
        time_range_json,
        filters_json,
        group_by_json,
        metrics_json,
        order_by_json,
        limit_size,
        row_count,
        snapshot_id,
        executed_result_json,
        result_digest_json,
        source_files_json,
        status,
        error_message,
        created_at
      ) VALUES ${rows
        .map(() => '(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
        .join(', ')}
      ON DUPLICATE KEY UPDATE
        response_text = VALUES(response_text),
        final_status = VALUES(final_status),
        query_plan_json = VALUES(query_plan_json),
        query_spec_json = VALUES(query_spec_json),
        executed_sql_text = VALUES(executed_sql_text),
        time_range_json = VALUES(time_range_json),
        filters_json = VALUES(filters_json),
        group_by_json = VALUES(group_by_json),
        metrics_json = VALUES(metrics_json),
        order_by_json = VALUES(order_by_json),
        limit_size = VALUES(limit_size),
        row_count = VALUES(row_count),
        snapshot_id = VALUES(snapshot_id),
        executed_result_json = VALUES(executed_result_json),
        result_digest_json = VALUES(result_digest_json),
        source_files_json = VALUES(source_files_json),
        status = VALUES(status),
        error_message = VALUES(error_message)`;

    const params = rows.flatMap((entry) => [
      String(entry.query_id || ''),
      String(entry.session_id || ''),
      Number(entry.turn_id || 0),
      entry.request_text ?? null,
      entry.response_text ?? null,
      entry.input_type ?? null,
      entry.intent ?? null,
      entry.answer_type ?? null,
      entry.final_status ?? null,
      String(entry.query_type || ''),
      jsonStringify(entry.query_plan_json, {}),
      jsonStringify(entry.query_spec_json, {}),
      entry.sql_fingerprint ?? null,
      entry.executed_sql_text ?? null,
      jsonStringify(entry.time_range_json, {}),
      jsonStringify(entry.filters_json, {}),
      jsonStringify(entry.group_by_json, null),
      jsonStringify(entry.metrics_json, null),
      jsonStringify(entry.order_by_json, null),
      entry.limit_size ?? null,
      Number(entry.row_count || 0),
      entry.snapshot_id ?? null,
      jsonStringify(entry.executed_result_json, null),
      jsonStringify(entry.result_digest_json, null),
      jsonStringify(entry.source_files_json, null),
      String(entry.status || 'succeeded'),
      entry.error_message ?? null,
      entry.created_at ?? new Date(),
    ]);

    await connection.query(sql, params);
  });
}

export async function parseAgentChatV2Response(response) {
  const raw = await response.text();
  let data = {};
  if (raw) {
    try {
      data = JSON.parse(raw);
    } catch {
      data = { detail: raw };
    }
  }
  if (!response.ok) {
    throw new Error(data?.detail || data?.error || raw || 'agent request failed');
  }
  return data;
}

async function callAgentChatV2({ agentBaseUrl, message, sessionId, turnId, timezone, currentContext }) {
  const response = await fetch(`${agentBaseUrl}/chat-v2`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      turn_id: turnId,
      timezone,
      current_context: currentContext ?? null,
    }),
    cache: 'no-store',
  });
  return await parseAgentChatV2Response(response);
}

export async function runAgentChatTurn({
  sessionId,
  turnId,
  clientMessageId,
  message,
  timezone,
  currentContext,
  agentBaseUrl,
}) {
  const normalizedMessage = String(message || '').trim();
  const normalizedSessionId = String(sessionId || '').trim();
  const normalizedClientMessageId = String(clientMessageId || '').trim();
  const normalizedTurnId = Number(turnId || 0);

  if (!normalizedSessionId) {
    throw new Error('session_id is required');
  }
  if (!Number.isInteger(normalizedTurnId) || normalizedTurnId <= 0) {
    throw new Error('turn_id is required');
  }
  if (!normalizedClientMessageId) {
    throw new Error('client_message_id is required');
  }
  if (!normalizedMessage) {
    throw new Error('message is required');
  }

  const agentResult = await callAgentChatV2({
    agentBaseUrl,
    message: normalizedMessage,
    sessionId: normalizedSessionId,
    turnId: normalizedTurnId,
    timezone: timezone || 'Asia/Shanghai',
    currentContext: currentContext ?? null,
  });

  await insertQueryLogs(agentResult.query_log_entries);

  return {
    session_id: normalizedSessionId,
    turn_id: Number(agentResult.turn_id || normalizedTurnId),
    answer_kind: agentResult.answer_kind || 'fallback',
    capability: agentResult.capability || 'none',
    final_text: agentResult.final_text || '',
    blocks: Array.isArray(agentResult.blocks) ? agentResult.blocks : [],
    topic: parseJsonValue(agentResult.topic) || {
      topic_family: null,
      active_topic_turn_id: null,
      primary_block_id: null,
    },
    query_ref: parseJsonValue(agentResult.query_ref) || { has_query: false, snapshot_ids: [] },
    turn_context: parseJsonValue(agentResult.turn_context) || currentContext || null,
    conversation_closed: Boolean(agentResult.conversation_closed),
    session_reset: Boolean(agentResult.session_reset),
  };
}
