import { useAuthStore } from '../store/authStore';

export interface SoilRecord {
  record_id: string;
  device_sn?: string | null;
  city_name?: string | null;
  county_name?: string | null;
  town_name?: string | null;
  device_name?: string | null;
  longitude?: number | string | null;
  latitude?: number | string | null;
  sample_time?: string | null;
  water20cm?: number | string | null;
  water40cm?: number | string | null;
  water60cm?: number | string | null;
  water80cm?: number | string | null;
  t20cm?: number | string | null;
  t40cm?: number | string | null;
  t60cm?: number | string | null;
  t80cm?: number | string | null;
  soil_anomaly_type?: string | null;
  soil_anomaly_score?: number | string | null;
  source_file?: string | null;
  source_sheet?: string | null;
  source_row?: number | string | null;
  [key: string]: unknown;
}

export interface SoilRecordQuery {
  page: number;
  page_size: number;
  city_name?: string;
  county_name?: string;
  device_sn?: string;
  soil_anomaly_type?: string;
  sample_time_from?: string;
  sample_time_to?: string;
}

export interface SoilRecordPage {
  rows: SoilRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SoilUploadInput {
  file: File;
  mode: 'incremental' | 'replace';
  confirm_full_replace: boolean;
}

export interface SoilUploadResult {
  filename: string;
  mode: string;
  raw_rows: number;
  loaded_rows: number;
}

export interface SoilMutationResult {
  record_id?: string;
  field?: string;
  old_value?: unknown;
  new_value?: unknown;
  deleted_count?: number;
  records?: SoilRecord[];
}

function authHeaders(json = false): Record<string, string> {
  const token = useAuthStore.getState().token;
  return {
    ...(json ? { 'Content-Type': 'application/json' } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {})
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
  appendParam(params, 'city_name', query.city_name);
  appendParam(params, 'county_name', query.county_name);
  appendParam(params, 'device_sn', query.device_sn);
  appendParam(params, 'soil_anomaly_type', query.soil_anomaly_type);
  appendParam(params, 'sample_time_from', query.sample_time_from);
  appendParam(params, 'sample_time_to', query.sample_time_to);

  return requestJson<SoilRecordPage>(`/api/admin/soil/records?${params.toString()}`, {
    method: 'GET',
    headers: authHeaders()
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
      confirm_full_replace: input.confirm_full_replace
    })
  });
}

export async function updateSoilRecordField(recordId: string, field: string, value: unknown): Promise<SoilMutationResult> {
  return requestJson<SoilMutationResult>(`/api/admin/soil/records/${encodeURIComponent(recordId)}`, {
    method: 'PATCH',
    headers: authHeaders(true),
    body: JSON.stringify({ field, value })
  });
}

export async function deleteSoilRecord(recordId: string): Promise<SoilMutationResult> {
  return requestJson<SoilMutationResult>(`/api/admin/soil/records/${encodeURIComponent(recordId)}`, {
    method: 'DELETE',
    headers: authHeaders()
  });
}

export async function bulkDeleteSoilRecords(recordIds: string[]): Promise<SoilMutationResult> {
  return requestJson<SoilMutationResult>('/api/admin/soil/records/bulk-delete', {
    method: 'POST',
    headers: authHeaders(true),
    body: JSON.stringify({ record_ids: recordIds })
  });
}
