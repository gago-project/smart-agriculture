import { useAuthStore } from '../store/authStore';

export interface SoilRecord {
  id: string;
  sn?: string | null;
  gatewayid?: string | null;
  sensorid?: string | null;
  unitid?: string | null;
  city?: string | null;
  county?: string | null;
  time?: string | null;
  create_time?: string | null;
  water20cm?: number | string | null;
  water40cm?: number | string | null;
  water60cm?: number | string | null;
  water80cm?: number | string | null;
  t20cm?: number | string | null;
  t40cm?: number | string | null;
  t60cm?: number | string | null;
  t80cm?: number | string | null;
  water20cmfieldstate?: string | null;
  water40cmfieldstate?: string | null;
  water60cmfieldstate?: string | null;
  water80cmfieldstate?: string | null;
  t20cmfieldstate?: string | null;
  t40cmfieldstate?: string | null;
  t60cmfieldstate?: string | null;
  t80cmfieldstate?: string | null;
  lat?: number | string | null;
  lon?: number | string | null;
  source_file?: string | null;
  source_sheet?: string | null;
  source_row?: number | string | null;
  [key: string]: unknown;
}

export interface SoilRecordQuery {
  page: number;
  page_size: number;
  city?: string;
  county?: string;
  sn?: string;
  create_time_from?: string;
  create_time_to?: string;
}

export interface SoilRecordPage {
  rows: SoilRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export type SoilImportMode = 'incremental' | 'replace';
export type SoilImportJobStatus = 'previewing' | 'ready' | 'applying' | 'succeeded' | 'failed';
export type SoilImportDiffType = 'all' | 'create' | 'update' | 'unchanged' | 'delete' | 'invalid';

export interface SoilUploadInput {
  file: File;
  mode: SoilImportMode;
  confirm_full_replace: boolean;
}

export interface SoilUploadResult {
  filename: string;
  mode: string;
  raw_rows: number;
  loaded_rows: number;
  invalid_rows?: number;
}

export interface SoilMutationResult {
  id?: string;
  field?: string;
  old_value?: unknown;
  new_value?: unknown;
  deleted_count?: number;
  records?: SoilRecord[];
  record?: SoilRecord | null;
}

export interface SoilImportSummary {
  raw_rows: number;
  valid_rows: number;
  invalid_rows: number;
  create_rows: number;
  update_rows: number;
  unchanged_rows: number;
  delete_rows: number;
  apply_rows: number;
}

export interface SoilImportJob {
  job_id: string;
  filename: string;
  status: SoilImportJobStatus;
  apply_mode?: SoilImportMode | null;
  processed_rows: number;
  total_rows: number;
  summary: SoilImportSummary | null;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  finished_at?: string | null;
}

export interface SoilImportFieldChange {
  before: unknown;
  after: unknown;
}

export interface SoilImportDiffRow {
  diff_id: number;
  diff_type: Exclude<SoilImportDiffType, 'all'>;
  id?: string | null;
  source_row?: number | null;
  db_record?: SoilRecord | null;
  import_record?: SoilRecord | null;
  field_changes?: Record<string, SoilImportFieldChange> | { reason: string } | null;
  created_at?: string | null;
}

export interface SoilImportDiffPage {
  rows: SoilImportDiffRow[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  summary?: SoilImportSummary | null;
  status?: SoilImportJobStatus;
}

function authHeaders(json = false): Record<string, string> {
  const token = useAuthStore.getState().token;
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

function extractError(payload: unknown): string {
  if (payload && typeof payload === 'object' && 'error' in payload && typeof payload.error === 'string') {
    return payload.error;
  }
  return '墒情管理服务暂时不可用，请稍后重试';
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

async function requestJson<T>(url: string, init: RequestInit): Promise<T> {
  const response = await fetch(url, init);
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

function bytesToBase64(bytes: Uint8Array): string {
  let binary = '';
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    const chunk = bytes.subarray(offset, offset + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

function readFileBytes(file: File): Promise<Uint8Array> {
  if (typeof file.arrayBuffer === 'function') {
    return file.arrayBuffer().then((buffer) => new Uint8Array(buffer));
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error('无法读取上传文件'));
    reader.onload = () => {
      if (!(reader.result instanceof ArrayBuffer)) {
        reject(new Error('无法读取上传文件'));
        return;
      }
      resolve(new Uint8Array(reader.result));
    };
    reader.readAsArrayBuffer(file);
  });
}

export async function fetchSoilRecords(query: SoilRecordQuery): Promise<SoilRecordPage> {
  const params = new URLSearchParams();
  appendParam(params, 'page', query.page);
  appendParam(params, 'page_size', query.page_size);
  appendParam(params, 'city', query.city);
  appendParam(params, 'county', query.county);
  appendParam(params, 'sn', query.sn);
  appendParam(params, 'create_time_from', query.create_time_from);
  appendParam(params, 'create_time_to', query.create_time_to);

  return requestJson<SoilRecordPage>(`/api/admin/soil/records?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(),
  });
}

export async function createSoilImportPreview(file: File): Promise<SoilImportJob> {
  const bytes = await readFileBytes(file);
  return requestJson<SoilImportJob>('/api/admin/soil/import-jobs', {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({
      filename: file.name,
      content_base64: bytesToBase64(bytes),
    }),
  });
}

export async function fetchSoilImportJob(jobId: string): Promise<SoilImportJob> {
  return requestJson<SoilImportJob>(`/api/admin/soil/import-jobs/${encodeURIComponent(jobId)}`, {
    method: 'GET',
    headers: authHeaders(),
  });
}

export async function fetchSoilImportDiff(jobId: string, query: {
  type?: SoilImportDiffType;
  page?: number;
  page_size?: number;
}): Promise<SoilImportDiffPage> {
  const params = new URLSearchParams();
  appendParam(params, 'type', query.type || 'all');
  appendParam(params, 'page', query.page || 1);
  appendParam(params, 'page_size', query.page_size || 20);

  return requestJson<SoilImportDiffPage>(`/api/admin/soil/import-jobs/${encodeURIComponent(jobId)}/diff?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders(),
  });
}

export async function applySoilImportJob(jobId: string, input: {
  mode: SoilImportMode;
  confirm_full_replace: boolean;
}): Promise<SoilImportJob> {
  return requestJson<SoilImportJob>(`/api/admin/soil/import-jobs/${encodeURIComponent(jobId)}/apply`, {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify(input),
  });
}

export async function uploadSoilExcel(input: SoilUploadInput): Promise<SoilUploadResult> {
  const bytes = await readFileBytes(input.file);
  return requestJson<SoilUploadResult>('/api/admin/soil/upload', {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({
      filename: input.file.name,
      content_base64: bytesToBase64(bytes),
      mode: input.mode,
      confirm_full_replace: input.confirm_full_replace,
    }),
  });
}

export async function updateSoilRecordField(recordId: string, field: string, value: unknown): Promise<SoilMutationResult> {
  return requestJson<SoilMutationResult>(`/api/admin/soil/records/${encodeURIComponent(recordId)}`, {
    method: 'PATCH',
    headers: authHeaders(true),
    body: JSON.stringify({ field, value }),
  });
}

export async function deleteSoilRecord(recordId: string): Promise<SoilMutationResult> {
  return requestJson<SoilMutationResult>(`/api/admin/soil/records/${encodeURIComponent(recordId)}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
}

export async function bulkDeleteSoilRecords(recordIds: string[]): Promise<SoilMutationResult> {
  return requestJson<SoilMutationResult>('/api/admin/soil/records/bulk-delete', {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({ ids: recordIds }),
  });
}
