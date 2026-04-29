import { useAuthStore } from '../store/authStore';

export interface AgentQueryEvidenceEntry {
  query_id: string;
  entry_index: number;
  query_type: string;
  status: string;
  row_count: number;
  created_at: string;
  query_plan_json?: unknown;
  time_range_json?: unknown;
  filters_json?: unknown;
  executed_sql_text?: string | null;
  executed_result_json?: unknown;
  result_preview?: unknown;
  preview_columns?: string[];
  result_truncated?: boolean;
  result_chars?: number;
  has_full_result?: boolean;
  missing_fields: string[];
}

export interface AgentQueryEvidencePayload {
  session_id: string;
  turn_id: number;
  has_query: boolean;
  entries: AgentQueryEvidenceEntry[];
}

export interface AgentQueryEvidenceResultPayload {
  query_id: string;
  executed_result_json?: unknown;
  result_chars?: number;
}

function authHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function extractError(payload: unknown): string {
  if (payload && typeof payload === 'object' && 'error' in payload && typeof payload.error === 'string') {
    return payload.error;
  }
  return '查询证据服务暂时不可用，请稍后重试';
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

export async function fetchAdminQueryEvidence(sessionId: string, turnId: number): Promise<AgentQueryEvidencePayload> {
  const params = new URLSearchParams({
    session_id: sessionId,
    turn_id: String(turnId),
  });
  const response = await fetch(`/api/admin/agent/query-evidence?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(),
    cache: 'no-store',
  });
  const payload = await parseJson(response);
  if (!response.ok) {
    if (response.status === 401) {
      useAuthStore.getState().clearSession();
      throw new Error('登录已失效，请重新登录');
    }
    throw new Error(extractError(payload));
  }
  return payload as AgentQueryEvidencePayload;
}

export async function fetchAdminQueryEvidenceResult(queryId: string): Promise<AgentQueryEvidenceResultPayload> {
  const params = new URLSearchParams({
    query_id: queryId,
  });
  const response = await fetch(`/api/admin/agent/query-evidence/result?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(),
    cache: 'no-store',
  });
  const payload = await parseJson(response);
  if (!response.ok) {
    if (response.status === 401) {
      useAuthStore.getState().clearSession();
      throw new Error('登录已失效，请重新登录');
    }
    throw new Error(extractError(payload));
  }
  return payload as AgentQueryEvidenceResultPayload;
}
