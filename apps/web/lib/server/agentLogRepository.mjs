import { withMysqlConnection } from './mysql.mjs';

const MAX_INLINE_EVIDENCE_RESULT_CHARS = 200_000;
const RESULT_PREVIEW_ROW_LIMIT = 10;
const RECORD_PREVIEW_COLUMNS = ['create_time', 'latest_create_time', 'city', 'county', 'sn', 'water20cm', 't20cm'];
const REGION_PREVIEW_COLUMNS = ['region', 'city', 'county', 'record_count', 'device_count', 'avg_water20cm', 'latest_create_time'];
const COMPARISON_PREVIEW_COLUMNS = ['rank', 'name', 'entity', 'city', 'county', 'record_count', 'device_count', 'region_count', 'avg_water20cm', 'latest_create_time'];

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

function appendFilter(filters, params, condition, value) {
  const normalized = String(value || '').trim();
  if (!normalized) return;
  filters.push(condition);
  params.push(normalized);
}

function toPositiveNumber(value) {
  const numeric = Number(value || 0);
  return Number.isFinite(numeric) && numeric > 0 ? numeric : 0;
}

function pickDefinedColumns(sample, candidates) {
  return candidates.filter((column) => Object.prototype.hasOwnProperty.call(sample, column));
}

function inferPreviewColumns(rows) {
  const sample = rows.find((row) => row && typeof row === 'object' && !Array.isArray(row));
  if (!sample) {
    return [];
  }
  if ('region' in sample && ('record_count' in sample || 'device_count' in sample)) {
    return pickDefinedColumns(sample, REGION_PREVIEW_COLUMNS);
  }
  if ('name' in sample || 'entity' in sample) {
    return pickDefinedColumns(sample, COMPARISON_PREVIEW_COLUMNS);
  }
  if ('sn' in sample && ('water20cm' in sample || 'create_time' in sample || 'latest_create_time' in sample)) {
    return pickDefinedColumns(sample, RECORD_PREVIEW_COLUMNS);
  }
  return Object.keys(sample).slice(0, 6);
}

function compactPreviewRows(rows, columns) {
  return rows.slice(0, RESULT_PREVIEW_ROW_LIMIT).map((row) => {
    if (!row || typeof row !== 'object' || Array.isArray(row)) {
      return row;
    }
    return Object.fromEntries(columns.map((column) => [column, row[column] ?? null]));
  });
}

function buildPreviewMeta({ totalRows, shownRows, sourceKey, columns }) {
  return {
    truncated: totalRows > shownRows,
    source_key: sourceKey || '',
    total_rows: totalRows,
    shown_rows: shownRows,
    hidden_columns: Array.isArray(columns) ? columns.length : 0,
  };
}

function buildResultPreview(value) {
  if (value === null || value === undefined) {
    return null;
  }
  if (Array.isArray(value)) {
    const previewColumns = inferPreviewColumns(value);
    return {
      rows: compactPreviewRows(value, previewColumns),
      preview_columns: previewColumns,
      _preview: buildPreviewMeta({
        totalRows: value.length,
        shownRows: Math.min(value.length, RESULT_PREVIEW_ROW_LIMIT),
        sourceKey: 'rows',
        columns: previewColumns,
      }),
    };
  }
  if (!value || typeof value !== 'object') {
    return value;
  }

  const record = value;
  const candidateKeys = ['rows', 'records', 'items', 'comparison', 'top_regions'];
  for (const key of candidateKeys) {
    const rows = Array.isArray(record[key]) ? record[key] : null;
    if (!rows) continue;
    const previewColumns = inferPreviewColumns(rows);
    return {
      ...record,
      [key]: compactPreviewRows(rows, previewColumns),
      preview_columns: previewColumns,
      _preview: buildPreviewMeta({
        totalRows: rows.length,
        shownRows: Math.min(rows.length, RESULT_PREVIEW_ROW_LIMIT),
        sourceKey: key,
        columns: previewColumns,
      }),
    };
  }

  if (record.latest_record && typeof record.latest_record === 'object' && !Array.isArray(record.latest_record)) {
    const previewColumns = inferPreviewColumns([record.latest_record]);
    return {
      ...record,
      latest_record: compactPreviewRows([record.latest_record], previewColumns)[0],
      preview_columns: previewColumns,
      _preview: buildPreviewMeta({
        totalRows: 1,
        shownRows: 1,
        sourceKey: 'latest_record',
        columns: previewColumns,
      }),
    };
  }

  return record;
}

function fromDbSummaryLog(row) {
  return {
    query_id: row.query_id,
    session_id: row.session_id,
    turn_id: row.turn_id,
    request_text: row.request_text,
    response_text: row.response_text,
    input_type: row.input_type,
    intent: row.intent,
    answer_type: row.answer_type,
    final_status: row.final_status,
    query_type: row.query_type,
    sql_fingerprint: row.sql_fingerprint,
    row_count: row.row_count,
    status: row.status,
    error_message: row.error_message,
    created_at: row.created_at,
    has_executed_sql_text: Boolean(row.has_executed_sql_text),
    has_executed_result_json: Boolean(row.has_executed_result_json),
  };
}

function fromDbDetailLog(row) {
  return {
    query_id: row.query_id,
    session_id: row.session_id,
    turn_id: row.turn_id,
    request_text: row.request_text,
    response_text: row.response_text,
    input_type: row.input_type,
    intent: row.intent,
    answer_type: row.answer_type,
    final_status: row.final_status,
    query_type: row.query_type,
    sql_fingerprint: row.sql_fingerprint,
    executed_sql_text: row.executed_sql_text,
    row_count: row.row_count,
    status: row.status,
    error_message: row.error_message,
    created_at: row.created_at,
    query_plan_json: parseJsonValue(row.query_plan_json),
    time_range_json: parseJsonValue(row.time_range_json),
    filters_json: parseJsonValue(row.filters_json),
    executed_result_json: parseJsonValue(row.executed_result_json),
    source_files_json: parseJsonValue(row.source_files_json),
    has_executed_sql_text: Boolean(row.executed_sql_text),
    has_executed_result_json: row.executed_result_json !== null && row.executed_result_json !== undefined,
  };
}

function fromDbEvidenceEntry(row, entryIndex) {
  const resultChars = toPositiveNumber(row.result_chars);
  const rawResult = parseJsonValue(row.executed_result_json);
  const inlineResultAllowed = rawResult !== null && resultChars <= MAX_INLINE_EVIDENCE_RESULT_CHARS;
  const previewResult = rawResult === null ? null : (inlineResultAllowed ? rawResult : buildResultPreview(rawResult));
  const missingFields = [];
  if (!row.executed_sql_text) {
    missingFields.push('executed_sql_text');
  }
  if (row.executed_result_json === null || row.executed_result_json === undefined) {
    missingFields.push('executed_result_json');
  }
  return {
    query_id: row.query_id,
    entry_index: entryIndex,
    query_type: row.query_type,
    status: row.status,
    row_count: Number(row.row_count || 0),
    created_at: row.created_at,
    query_plan_json: parseJsonValue(row.query_plan_json),
    time_range_json: parseJsonValue(row.time_range_json),
    filters_json: parseJsonValue(row.filters_json),
    executed_sql_text: row.executed_sql_text || null,
    executed_result_json: inlineResultAllowed ? rawResult : null,
    result_preview: previewResult,
    preview_columns: Array.isArray(previewResult?.preview_columns) ? previewResult.preview_columns : [],
    result_truncated: rawResult !== null && !inlineResultAllowed,
    result_chars: resultChars,
    has_full_result: rawResult !== null,
    missing_fields: missingFields,
  };
}

export async function listAgentQueryLogs(query) {
  return await withMysqlConnection(async (connection) => {
    const filters = [];
    const params = [];

    appendFilter(filters, params, 'session_id LIKE ?', query.session_id ? `%${query.session_id}%` : '');
    appendFilter(filters, params, 'query_type = ?', query.query_type);
    appendFilter(filters, params, 'status = ?', query.status);
    appendFilter(filters, params, 'intent = ?', query.intent);

    const keyword = String(query.keyword || '').trim();
    if (keyword) {
      filters.push('(request_text LIKE ? OR response_text LIKE ? OR query_id LIKE ? OR session_id LIKE ? OR executed_sql_text LIKE ?)');
      params.push(`%${keyword}%`, `%${keyword}%`, `%${keyword}%`, `%${keyword}%`, `%${keyword}%`);
    }

    appendFilter(filters, params, 'created_at >= ?', query.created_at_from);
    appendFilter(filters, params, 'created_at <= ?', query.created_at_to);

    const whereClause = filters.length > 0 ? `WHERE ${filters.join(' AND ')}` : '';
    const page = Math.max(1, Number(query.page || 1));
    const pageSize = Math.min(100, Math.max(1, Number(query.page_size || 30)));
    const offset = (page - 1) * pageSize;

    const [countRows] = await connection.query(
      `SELECT COUNT(*) AS total FROM agent_query_log ${whereClause}`,
      params,
    );

    const [pageRows] = await connection.query(
      `SELECT query_id
       FROM agent_query_log
       ${whereClause}
       ORDER BY created_at DESC
       LIMIT ${pageSize} OFFSET ${offset}`,
      params,
    );

    const total = Number(countRows[0]?.total || 0);
    const pageIds = pageRows.map((row) => row.query_id).filter(Boolean);
    if (pageIds.length === 0) {
      return {
        rows: [],
        total,
        page,
        page_size: pageSize,
        total_pages: total === 0 ? 0 : Math.ceil(total / pageSize),
      };
    }

    const detailPlaceholders = pageIds.map(() => '?').join(', ');
    const [detailRows] = await connection.query(
      `SELECT
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
         sql_fingerprint,
         row_count,
         status,
         error_message,
         DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS created_at,
         IF(executed_sql_text IS NULL OR executed_sql_text = '', 0, 1) AS has_executed_sql_text,
         IF(executed_result_json IS NULL, 0, 1) AS has_executed_result_json
       FROM agent_query_log
       WHERE query_id IN (${detailPlaceholders})`,
      pageIds,
    );

    const rowsById = new Map(detailRows.map((row) => [row.query_id, row]));
    return {
      rows: pageIds.map((queryId) => rowsById.get(queryId)).filter(Boolean).map(fromDbSummaryLog),
      total,
      page,
      page_size: pageSize,
      total_pages: total === 0 ? 0 : Math.ceil(total / pageSize),
    };
  });
}

export async function getAgentQueryLogDetail(queryId) {
  return await withMysqlConnection(async (connection) => {
    const [rows] = await connection.query(
      `SELECT
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
         sql_fingerprint,
         executed_sql_text,
         row_count,
         status,
         error_message,
         DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS created_at,
         query_plan_json,
         time_range_json,
         filters_json,
         executed_result_json,
         source_files_json
       FROM agent_query_log
       WHERE query_id = ?
       LIMIT 1`,
      [String(queryId || '').trim()],
    );

    const row = rows[0];
    if (!row) {
      throw new Error('查询日志不存在');
    }
    return fromDbDetailLog(row);
  });
}

export async function getAgentQueryEvidenceByTurn({ session_id, turn_id }) {
  return await withMysqlConnection(async (connection) => {
    const sessionId = String(session_id || '').trim();
    const turnId = Number(turn_id || 0);
    if (!sessionId || !Number.isInteger(turnId) || turnId <= 0) {
      throw new Error('session_id and turn_id are required');
    }

    const [orderRows] = await connection.query(
      `SELECT
         query_id,
         DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS created_at
       FROM agent_query_log
       FORCE INDEX (idx_aql_session_turn)
       WHERE session_id = ?
         AND turn_id = ?
       ORDER BY created_at ASC, query_id ASC`,
      [sessionId, turnId],
    );

    const orderedIds = orderRows.map((row) => row.query_id).filter(Boolean);
    if (orderedIds.length === 0) {
      return {
        session_id: sessionId,
        turn_id: turnId,
        has_query: false,
        entries: [],
      };
    }

    const detailPlaceholders = orderedIds.map(() => '?').join(', ');
    const [detailRows] = await connection.query(
      `SELECT
         query_id,
         query_type,
         status,
         row_count,
         DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%s') AS created_at,
         query_plan_json,
         time_range_json,
         filters_json,
         executed_sql_text,
         executed_result_json,
         CHAR_LENGTH(CAST(executed_result_json AS CHAR)) AS result_chars
       FROM agent_query_log
       WHERE query_id IN (${detailPlaceholders})`,
      orderedIds,
    );

    const rowsById = new Map(detailRows.map((row) => [row.query_id, row]));

    return {
      session_id: sessionId,
      turn_id: turnId,
      has_query: orderedIds.length > 0,
      entries: orderedIds
        .map((queryId, index) => {
          const row = rowsById.get(queryId);
          return row ? fromDbEvidenceEntry(row, index + 1) : null;
        })
        .filter(Boolean),
    };
  });
}

export async function getAgentQueryEvidenceResultByQueryId(query_id) {
  return await withMysqlConnection(async (connection) => {
    const queryId = String(query_id || '').trim();
    if (!queryId) {
      throw new Error('query_id is required');
    }

    const [rows] = await connection.query(
      `SELECT
         query_id,
         executed_result_json,
         CHAR_LENGTH(CAST(executed_result_json AS CHAR)) AS result_chars
       FROM agent_query_log
       WHERE query_id = ?
       LIMIT 1`,
      [queryId],
    );

    const row = rows[0];
    if (!row) {
      throw new Error('查询证据不存在');
    }

    return {
      query_id: row.query_id,
      executed_result_json: parseJsonValue(row.executed_result_json),
      result_chars: toPositiveNumber(row.result_chars),
    };
  });
}
