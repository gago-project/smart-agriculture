import crypto from 'node:crypto';

import { withMysqlConnection, withMysqlTransaction } from './mysql.mjs';

const SESSION_TITLE_MAX_LENGTH = 20;
const SNAPSHOT_PAGE_SIZE_DEFAULT = 50;
const CHAT_TXN_RETRY_LIMIT = 2;
const CHAT_TXN_RETRY_BACKOFF_MS = 100;

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

function buildSessionTitle(text) {
  const normalized = String(text || '').trim();
  return normalized.slice(0, SESSION_TITLE_MAX_LENGTH) || '新会话';
}

function jsonStringify(value, fallback) {
  try {
    return JSON.stringify(value ?? fallback);
  } catch {
    return JSON.stringify(fallback);
  }
}

function toPositiveInt(value, fallback = 0) {
  const numeric = Number(value);
  return Number.isInteger(numeric) && numeric > 0 ? numeric : fallback;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRetryableMysqlError(error) {
  if (!error || typeof error !== 'object') {
    return false;
  }
  const code = String(error.code || '');
  return code === 'ER_LOCK_DEADLOCK' || code === 'ER_LOCK_WAIT_TIMEOUT';
}

function formatTopicContext(currentContext) {
  const context = currentContext && typeof currentContext === 'object' ? currentContext : null;
  return {
    topic_family: typeof context?.topic_family === 'string' ? context.topic_family : null,
    active_topic_turn_id: Number.isInteger(context?.active_topic_turn_id) ? context.active_topic_turn_id : null,
    primary_block_id: typeof context?.primary_block_id === 'string' ? context.primary_block_id : null,
  };
}

function stripBlockRows(block) {
  if (!block || typeof block !== 'object' || Array.isArray(block)) {
    return block;
  }
  if (block.block_type !== 'list_table') {
    return block;
  }
  const next = { ...block };
  delete next.rows;
  delete next.items;
  return next;
}

function stripLargeBlocks(blocks) {
  return asArray(blocks).map((block) => stripBlockRows(block));
}

function buildBusySessionError() {
  return new Error('当前会话处理中，请稍后重试');
}

function isPendingTurnRow(row) {
  return Boolean(row) && row.answer_kind === 'pending';
}

async function loadSnapshotRows(connection, snapshotId, page, pageSize) {
  const safePage = Math.max(1, toPositiveInt(page, 1));
  const safePageSize = Math.min(100, Math.max(1, toPositiveInt(pageSize, SNAPSHOT_PAGE_SIZE_DEFAULT)));
  const offset = (safePage - 1) * safePageSize;
  const [rows] = await connection.execute(
    `SELECT payload_json
     FROM agent_result_snapshot_item
     WHERE snapshot_id = ?
     ORDER BY row_index ASC
     LIMIT ? OFFSET ?`,
    [snapshotId, safePageSize, offset],
  );
  return rows.map((row) => parseJsonValue(row.payload_json) || {});
}

async function hydrateListBlock(connection, block, requestedPage) {
  const pagination = block?.pagination && typeof block.pagination === 'object' ? block.pagination : {};
  const snapshotId = typeof pagination.snapshot_id === 'string' ? pagination.snapshot_id : '';
  if (!snapshotId) {
    return block;
  }
  const pageSize = Math.min(100, Math.max(1, toPositiveInt(pagination.page_size, SNAPSHOT_PAGE_SIZE_DEFAULT)));
  const totalCount = Math.max(0, toPositiveInt(pagination.total_count, 0));
  const page = Math.max(1, requestedPage || toPositiveInt(pagination.page, 1));
  const totalPages = totalCount === 0 ? 0 : Math.ceil(totalCount / pageSize);
  const rows = await loadSnapshotRows(connection, snapshotId, page, pageSize);
  return {
    ...block,
    rows,
    pagination: {
      ...pagination,
      page,
      page_size: pageSize,
      total_count: totalCount,
      total_pages: totalPages,
      snapshot_id: snapshotId,
    },
  };
}

async function hydrateTurnBlocks(connection, blocks, requestedBlockId = null, requestedPage = null) {
  const hydrated = [];
  for (const block of asArray(blocks)) {
    if (block?.block_type === 'list_table') {
      const shouldHydrate = !requestedBlockId || block.block_id === requestedBlockId;
      hydrated.push(
        shouldHydrate ? await hydrateListBlock(connection, block, requestedPage) : await hydrateListBlock(connection, block, null),
      );
      continue;
    }
    hydrated.push(block);
  }
  return hydrated;
}

async function retryMysqlOperation(operation, exhaustedMessage = '当前会话处理中，请稍后重试') {
  let attempt = 0;
  while (attempt <= CHAT_TXN_RETRY_LIMIT) {
    try {
      return await operation();
    } catch (error) {
      if (attempt >= CHAT_TXN_RETRY_LIMIT || !isRetryableMysqlError(error)) {
        if (isRetryableMysqlError(error)) {
          throw new Error(exhaustedMessage);
        }
        throw error;
      }
      attempt += 1;
      await sleep(CHAT_TXN_RETRY_BACKOFF_MS * attempt);
    }
  }
  throw new Error(exhaustedMessage);
}

function normalizeTurnRecord(row, hydratedBlocks) {
  const queryRef = parseJsonValue(row.query_ref_json) || { has_query: false, snapshot_ids: [] };
  const blocks = hydratedBlocks ?? parseJsonValue(row.blocks_json) ?? [];
  return {
    session_id: row.session_id,
    turn_id: Number(row.turn_id || 0),
    answer_kind: row.answer_kind,
    capability: row.capability,
    final_text: row.final_text,
    user_text: row.user_text,
    blocks,
    primary_block_id: row.primary_block_id || null,
    query_ref: queryRef,
    created_at: row.created_at,
  };
}

function buildExistingTurnResponse(row, currentContext, hydratedBlocks) {
  return {
    ...normalizeTurnRecord(row, hydratedBlocks),
    topic: formatTopicContext(currentContext),
    conversation_closed: Boolean(currentContext?.closed),
    session_reset: false,
  };
}

async function loadTurnRowBySessionAndClient(connection, sessionId, clientMessageId, { forUpdate = false } = {}) {
  const suffix = forUpdate ? 'FOR UPDATE' : 'LIMIT 1';
  const [rows] = await connection.execute(
    `SELECT
       session_id,
       turn_id,
       user_text,
       answer_kind,
       capability,
       final_text,
       blocks_json,
       primary_block_id,
       query_ref_json,
       DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS created_at
     FROM agent_chat_turn
     WHERE session_id = ? AND client_message_id = ?
     ${suffix}`,
    [sessionId, clientMessageId],
  );
  return rows[0] || null;
}

async function insertQueryLogs(connection, entries) {
  const rows = asArray(entries).filter((entry) => entry && typeof entry === 'object' && entry.query_id);
  if (rows.length === 0) {
    return;
  }

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

async function reserveChatTurn({ ownerUserId, sessionId, clientMessageId, message }) {
  return await withMysqlTransaction(async (connection) => {
    const [sessionRows] = await connection.execute(
      `SELECT session_id, owner_user_id, title, last_turn_id, current_context_json, archived_at
       FROM agent_chat_session
       WHERE session_id = ? AND owner_user_id = ?
       FOR UPDATE`,
      [sessionId, ownerUserId],
    );
    const sessionRow = sessionRows[0];
    if (!sessionRow) {
      throw new Error('会话不存在或无权限访问');
    }
    if (sessionRow.archived_at) {
      throw new Error('会话已归档，请新建会话继续提问');
    }

    const currentContext = parseJsonValue(sessionRow.current_context_json) || null;
    const existingTurnRow = await loadTurnRowBySessionAndClient(connection, sessionId, clientMessageId);
    if (existingTurnRow) {
      if (isPendingTurnRow(existingTurnRow)) {
        return {
          status: 'pending',
          turnId: Number(existingTurnRow.turn_id || 0),
        };
      }
      const blocks = await hydrateTurnBlocks(connection, parseJsonValue(existingTurnRow.blocks_json) || []);
      return {
        status: 'existing',
        response: buildExistingTurnResponse(existingTurnRow, currentContext, blocks),
      };
    }

    const [pendingRows] = await connection.execute(
      `SELECT turn_id
       FROM agent_chat_turn
       WHERE session_id = ? AND answer_kind = 'pending'
       FOR UPDATE`,
      [sessionId],
    );
    if (pendingRows[0]) {
      throw buildBusySessionError();
    }

    const turnId = Number(sessionRow.last_turn_id || 0) + 1;
    await connection.execute(
      `INSERT INTO agent_chat_turn (
         session_id,
         turn_id,
         client_message_id,
         user_text,
         answer_kind,
         capability,
         final_text,
         blocks_json,
         primary_block_id,
         query_ref_json,
         created_at
       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW())`,
      [
        sessionId,
        turnId,
        clientMessageId,
        message,
        'pending',
        'pending',
        '',
        jsonStringify([], []),
        null,
        jsonStringify({ has_query: false, snapshot_ids: [] }, { has_query: false, snapshot_ids: [] }),
      ],
    );
    await connection.execute(
      `UPDATE agent_chat_session
       SET last_turn_id = ?, updated_at = NOW()
       WHERE session_id = ?`,
      [turnId, sessionId],
    );

    return {
      status: 'reserved',
      turnId,
      currentContext,
      shouldUpdateTitle: Number(sessionRow.last_turn_id || 0) === 0,
    };
  });
}

async function finalizeReservedChatTurn({
  ownerUserId,
  sessionId,
  clientMessageId,
  turnId,
  message,
  currentContext,
  shouldUpdateTitle,
  agentResult,
}) {
  return await withMysqlTransaction(async (connection) => {
    const [sessionRows] = await connection.execute(
      `SELECT session_id, owner_user_id, title, current_context_json, archived_at
       FROM agent_chat_session
       WHERE session_id = ? AND owner_user_id = ?
       FOR UPDATE`,
      [sessionId, ownerUserId],
    );
    const sessionRow = sessionRows[0];
    if (!sessionRow) {
      throw new Error('会话不存在或无权限访问');
    }
    if (sessionRow.archived_at) {
      throw new Error('会话已归档，请新建会话继续提问');
    }

    const storedTurnRow = await loadTurnRowBySessionAndClient(connection, sessionId, clientMessageId, { forUpdate: true });
    if (!storedTurnRow) {
      throw new Error('轮次不存在或已取消');
    }
    if (!isPendingTurnRow(storedTurnRow)) {
      const blocks = await hydrateTurnBlocks(connection, parseJsonValue(storedTurnRow.blocks_json) || []);
      return buildExistingTurnResponse(
        storedTurnRow,
        parseJsonValue(sessionRow.current_context_json) || null,
        blocks,
      );
    }

    const storedBlocks = stripLargeBlocks(agentResult.blocks);
    const nextContext = agentResult.turn_context ?? currentContext ?? parseJsonValue(sessionRow.current_context_json) ?? null;
    await connection.execute(
      `UPDATE agent_chat_turn
       SET user_text = ?,
           answer_kind = ?,
           capability = ?,
           final_text = ?,
           blocks_json = ?,
           primary_block_id = ?,
           query_ref_json = ?
       WHERE session_id = ? AND turn_id = ? AND client_message_id = ?`,
      [
        message,
        agentResult.answer_kind || 'fallback',
        agentResult.capability || 'none',
        agentResult.final_text || '',
        jsonStringify(storedBlocks, []),
        agentResult.topic?.primary_block_id ?? agentResult.primary_block_id ?? null,
        jsonStringify(agentResult.query_ref, { has_query: false, snapshot_ids: [] }),
        sessionId,
        turnId,
        clientMessageId,
      ],
    );
    await connection.execute(
      `UPDATE agent_chat_session
       SET title = ?, current_context_json = ?, updated_at = NOW()
       WHERE session_id = ?`,
      [
        shouldUpdateTitle ? buildSessionTitle(message) : sessionRow.title,
        jsonStringify(nextContext, null),
        sessionId,
      ],
    );
    await insertQueryLogs(connection, agentResult.query_log_entries);

    return {
      session_id: sessionId,
      turn_id: turnId,
      answer_kind: agentResult.answer_kind || 'fallback',
      capability: agentResult.capability || 'none',
      final_text: agentResult.final_text || '',
      blocks: asArray(agentResult.blocks),
      topic: agentResult.topic ?? formatTopicContext(nextContext),
      query_ref: agentResult.query_ref ?? { has_query: false, snapshot_ids: [] },
      conversation_closed: Boolean(agentResult.conversation_closed),
      session_reset: Boolean(agentResult.session_reset),
    };
  });
}

async function abortReservedChatTurn({ ownerUserId, sessionId, clientMessageId, turnId }) {
  return await withMysqlTransaction(async (connection) => {
    const [sessionRows] = await connection.execute(
      `SELECT session_id, owner_user_id, last_turn_id
       FROM agent_chat_session
       WHERE session_id = ? AND owner_user_id = ?
       FOR UPDATE`,
      [sessionId, ownerUserId],
    );
    const sessionRow = sessionRows[0];
    if (!sessionRow) {
      return;
    }

    const [deleteResult] = await connection.execute(
      `DELETE FROM agent_chat_turn
       WHERE session_id = ? AND turn_id = ? AND client_message_id = ? AND answer_kind = 'pending'`,
      [sessionId, turnId, clientMessageId],
    );
    if (deleteResult.affectedRows && Number(sessionRow.last_turn_id || 0) === turnId) {
      await connection.execute(
        `UPDATE agent_chat_session
         SET last_turn_id = ?, updated_at = NOW()
         WHERE session_id = ?`,
        [Math.max(0, turnId - 1), sessionId],
      );
    }
  });
}

async function runChatTurnTransaction({ ownerUserId, sessionId, clientMessageId, message, timezone, agentBaseUrl }) {
  const reservedTurn = await retryMysqlOperation(() =>
    reserveChatTurn({
      ownerUserId,
      sessionId,
      clientMessageId,
      message,
    }),
  );
  if (reservedTurn.status === 'existing') {
    return reservedTurn.response;
  }
  if (reservedTurn.status === 'pending') {
    throw buildBusySessionError();
  }

  let agentResult;
  try {
    agentResult = await callAgentChatV2({
      agentBaseUrl,
      message,
      sessionId,
      turnId: reservedTurn.turnId,
      timezone,
      currentContext: reservedTurn.currentContext,
    });
  } catch (error) {
    try {
      await retryMysqlOperation(() =>
        abortReservedChatTurn({
          ownerUserId,
          sessionId,
          clientMessageId,
          turnId: reservedTurn.turnId,
        }),
      );
    } catch (abortError) {
      console.error('failed to abort reserved chat turn', abortError);
    }
    throw error;
  }

  return await retryMysqlOperation(() =>
    finalizeReservedChatTurn({
      ownerUserId,
      sessionId,
      clientMessageId,
      turnId: reservedTurn.turnId,
      message,
      currentContext: reservedTurn.currentContext,
      shouldUpdateTitle: reservedTurn.shouldUpdateTitle,
      agentResult,
    }),
  );
}

export async function createChatSession({ ownerUserId, title }) {
  const sessionId = crypto.randomUUID();
  const sessionTitle = buildSessionTitle(title);
  await withMysqlConnection(async (connection) => {
    await connection.execute(
      `INSERT INTO agent_chat_session (
         session_id,
         owner_user_id,
         title,
         last_turn_id,
         current_context_json,
         created_at,
         updated_at,
         archived_at
       ) VALUES (?, ?, ?, 0, NULL, NOW(), NOW(), NULL)`,
      [sessionId, ownerUserId, sessionTitle],
    );
  });
  return {
    session_id: sessionId,
    title: sessionTitle,
  };
}

export async function listChatSessions({ ownerUserId }) {
  return await withMysqlConnection(async (connection) => {
    const [rows] = await connection.execute(
      `SELECT
         s.session_id,
         s.title,
         s.last_turn_id,
         DATE_FORMAT(s.created_at, '%Y-%m-%d %H:%i:%s') AS created_at,
         DATE_FORMAT(s.updated_at, '%Y-%m-%d %H:%i:%s') AS updated_at,
         DATE_FORMAT(s.archived_at, '%Y-%m-%d %H:%i:%s') AS archived_at,
         t.user_text AS latest_user_text,
         t.final_text AS latest_answer_text
       FROM agent_chat_session s
       LEFT JOIN agent_chat_turn t
         ON t.session_id = s.session_id
        AND t.turn_id = (
          SELECT MAX(t2.turn_id)
          FROM agent_chat_turn t2
          WHERE t2.session_id = s.session_id AND t2.answer_kind <> 'pending'
        )
       WHERE s.owner_user_id = ? AND s.archived_at IS NULL
       ORDER BY s.updated_at DESC`,
      [ownerUserId],
    );
    return {
      sessions: rows.map((row) => ({
        session_id: row.session_id,
        title: row.title,
        last_turn_id: Number(row.last_turn_id || 0),
        created_at: row.created_at,
        updated_at: row.updated_at,
        latest_user_text: row.latest_user_text || '',
        latest_answer_text: row.latest_answer_text || '',
      })),
    };
  });
}

export async function getChatSessionDetail({ ownerUserId, sessionId }) {
  return await withMysqlConnection(async (connection) => {
    const [sessionRows] = await connection.execute(
      `SELECT
         session_id,
         title,
         last_turn_id,
         current_context_json,
         DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS created_at,
         DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%s') AS updated_at,
         DATE_FORMAT(archived_at, '%Y-%m-%d %H:%i:%s') AS archived_at
       FROM agent_chat_session
       WHERE session_id = ? AND owner_user_id = ?
       LIMIT 1`,
      [sessionId, ownerUserId],
    );
    const sessionRow = sessionRows[0];
    if (!sessionRow) {
      throw new Error('会话不存在或无权限访问');
    }
    const currentContext = parseJsonValue(sessionRow.current_context_json) || null;
    const [turnRows] = await connection.execute(
      `SELECT
         session_id,
         turn_id,
         user_text,
         answer_kind,
         capability,
         final_text,
         blocks_json,
         primary_block_id,
         query_ref_json,
         DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS created_at
       FROM agent_chat_turn
       WHERE session_id = ? AND answer_kind <> 'pending'
       ORDER BY turn_id ASC`,
      [sessionId],
    );
    const turns = [];
    for (const row of turnRows) {
      const blocks = await hydrateTurnBlocks(connection, parseJsonValue(row.blocks_json) || []);
      turns.push(normalizeTurnRecord(row, blocks));
    }
    return {
      session_id: sessionRow.session_id,
      title: sessionRow.title,
      last_turn_id: Number(sessionRow.last_turn_id || 0),
      created_at: sessionRow.created_at,
      updated_at: sessionRow.updated_at,
      archived_at: sessionRow.archived_at,
      topic: formatTopicContext(currentContext),
      turns,
    };
  });
}

export async function renameChatSession({ ownerUserId, sessionId, title }) {
  const sessionTitle = buildSessionTitle(title);
  return await withMysqlConnection(async (connection) => {
    const [result] = await connection.execute(
      `UPDATE agent_chat_session
       SET title = ?, updated_at = NOW()
       WHERE session_id = ? AND owner_user_id = ? AND archived_at IS NULL`,
      [sessionTitle, sessionId, ownerUserId],
    );
    if (!result.affectedRows) {
      throw new Error('会话不存在、已归档或无权限访问');
    }
    return {
      session_id: sessionId,
      title: sessionTitle,
    };
  });
}

export async function archiveChatSession({ ownerUserId, sessionId }) {
  return await withMysqlConnection(async (connection) => {
    const [result] = await connection.execute(
      `UPDATE agent_chat_session
       SET archived_at = NOW(), updated_at = NOW()
       WHERE session_id = ? AND owner_user_id = ? AND archived_at IS NULL`,
      [sessionId, ownerUserId],
    );
    if (!result.affectedRows) {
      throw new Error('会话不存在、已归档或无权限访问');
    }
    return { session_id: sessionId, archived: true };
  });
}

export async function getChatBlockPage({ ownerUserId, sessionId, turnId, blockId, page }) {
  return await withMysqlConnection(async (connection) => {
    const [sessionRows] = await connection.execute(
      `SELECT 1
       FROM agent_chat_session
       WHERE session_id = ? AND owner_user_id = ?
       LIMIT 1`,
      [sessionId, ownerUserId],
    );
    if (!sessionRows[0]) {
      throw new Error('会话不存在或无权限访问');
    }

    const [turnRows] = await connection.execute(
      `SELECT blocks_json
       FROM agent_chat_turn
       WHERE session_id = ? AND turn_id = ?
       LIMIT 1`,
      [sessionId, turnId],
    );
    const turnRow = turnRows[0];
    if (!turnRow) {
      throw new Error('轮次不存在');
    }

    const blocks = parseJsonValue(turnRow.blocks_json) || [];
    const matched = blocks.find((block) => block?.block_id === blockId);
    if (!matched) {
      throw new Error('区块不存在');
    }

    if (matched.block_type === 'list_table') {
      return await hydrateListBlock(connection, matched, Math.max(1, toPositiveInt(page, 1)));
    }
    return matched;
  });
}

export async function executeChatTurn({ ownerUserId, sessionId, clientMessageId, message, timezone, agentBaseUrl }) {
  const normalizedMessage = String(message || '').trim();
  if (!normalizedMessage) {
    throw new Error('message is required');
  }
  const normalizedSessionId = String(sessionId || '').trim();
  if (!normalizedSessionId) {
    throw new Error('session_id is required');
  }
  const normalizedClientMessageId = String(clientMessageId || '').trim();
  if (!normalizedClientMessageId) {
    throw new Error('client_message_id is required');
  }

  return await runChatTurnTransaction({
    ownerUserId,
    sessionId: normalizedSessionId,
    clientMessageId: normalizedClientMessageId,
    message: normalizedMessage,
    timezone: timezone || 'Asia/Shanghai',
    agentBaseUrl,
  });
}
