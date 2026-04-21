import { useAuthStore } from '../store/authStore';

export interface AgentQueryLog {
  query_id: string;
  session_id: string;
  turn_id: number;
  request_text?: string | null;
  response_text?: string | null;
  input_type?: string | null;
  intent?: string | null;
  answer_type?: string | null;
  final_status?: string | null;
  query_type?: string | null;
  sql_fingerprint?: string | null;
  executed_sql_text?: string | null;
  row_count: number;
  status: string;
  error_message?: string | null;
  created_at: string;
  query_plan_json?: unknown;
  time_range_json?: unknown;
  filters_json?: unknown;
  executed_result_json?: unknown;
  source_files_json?: unknown;
}

export interface AgentQueryLogQuery {
  page: number;
  page_size: number;
  keyword?: string;
  session_id?: string;
  query_type?: string;
  intent?: string;
  status?: string;
  created_at_from?: string;
  created_at_to?: string;
}

export interface AgentQueryLogPage {
  rows: AgentQueryLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function extractError(payload: unknown): string {
  if (payload && typeof payload === 'object' && 'error' in payload && typeof payload.error === 'string') {
    return payload.error;
  }
  return '查询日志服务暂时不可用，请稍后重试';
}

async function parseJson(response: Response): Promise<unknown> {
  try {
    return (await response.json()) as unknown;
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw new Error('响应格式不正确');
    }
    throw error;
  }
}

async function requestJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { method: 'GET', headers: authHeaders(), cache: 'no-store' });
  const payload = await parseJson(response);
  if (!response.ok) {
    if (response.status === 401) {
      useAuthStore.getState().clearSession();
      throw new Error('登录已失效，请重新登录');
    }
    throw new Error(extractError(payload));
  }
  return payload as T;
}

function appendParam(params: URLSearchParams, key: string, value: unknown) {
  if (value !== undefined && value !== null && String(value).trim() !== '') {
    params.set(key, String(value).trim());
  }
}

export async function fetchAgentQueryLogs(query: AgentQueryLogQuery): Promise<AgentQueryLogPage> {
  const params = new URLSearchParams();
  appendParam(params, 'page', query.page);
  appendParam(params, 'page_size', query.page_size);
  appendParam(params, 'keyword', query.keyword);
  appendParam(params, 'session_id', query.session_id);
  appendParam(params, 'query_type', query.query_type);
  appendParam(params, 'intent', query.intent);
  appendParam(params, 'status', query.status);
  appendParam(params, 'created_at_from', query.created_at_from);
  appendParam(params, 'created_at_to', query.created_at_to);

  return requestJson<AgentQueryLogPage>(`/api/developer/agent/query-logs?${params.toString()}`);
}
