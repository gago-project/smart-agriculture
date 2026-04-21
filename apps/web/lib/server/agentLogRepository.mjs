import { withMysqlConnection } from './mysql.mjs';

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

function fromDbLog(row) {
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
       ${whereClause}
       ORDER BY created_at DESC
       LIMIT ${pageSize} OFFSET ${offset}`,
      params,
    );

    const total = Number(countRows[0]?.total || 0);
    return {
      rows: rows.map(fromDbLog),
      total,
      page,
      page_size: pageSize,
      total_pages: total === 0 ? 0 : Math.ceil(total / pageSize),
    };
  });
}
