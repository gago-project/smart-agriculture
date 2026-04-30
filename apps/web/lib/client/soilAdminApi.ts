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
  [key: string]: unknown;
}

export interface SoilRecordPage {
  rows: SoilRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface RuleConfig {
  rule_id: string;
  rule_name: string;
  rule_type: string;
  rule_definition_json: string;
  enabled: boolean;
}

export interface TemplateConfig {
  template_id: string;
  template_name: string;
  template_text: string;
  render_mode: string;
}

async function parseJson<T>(response: Response): Promise<T> {
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload?.error || '后台接口调用失败');
  }
  return payload as T;
}

export async function fetchSoilRecords(query: Record<string, unknown>): Promise<SoilRecordPage> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      params.set(key, String(value));
    }
  }
  const response = await fetch(`/api/admin/soil/records?${params.toString()}`, { cache: 'no-store' });
  return parseJson<SoilRecordPage>(response);
}

export async function uploadSoilExcel(input: { file: File; mode: 'incremental' | 'replace'; confirm_full_replace: boolean }) {
  const buffer = await input.file.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  }
  const response = await fetch('/api/admin/soil/upload', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filename: input.file.name,
      content_base64: btoa(binary),
      mode: input.mode,
      confirm_full_replace: input.confirm_full_replace,
    }),
  });
  return parseJson<{ filename: string; mode: string; raw_rows: number; loaded_rows: number }>(response);
}

export async function updateSoilRecordField(recordId: string, field: string, value: unknown) {
  const response = await fetch(`/api/admin/soil/records/${encodeURIComponent(recordId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ field, value }),
  });
  return parseJson<{ id: string; field: string; old_value?: unknown; new_value?: unknown }>(response);
}

export async function deleteSoilRecord(recordId: string) {
  const response = await fetch(`/api/admin/soil/records/${encodeURIComponent(recordId)}`, { method: 'DELETE' });
  return parseJson<{ deleted_count: number }>(response);
}

export async function bulkDeleteSoilRecords(ids: string[]) {
  const response = await fetch('/api/admin/soil/records/bulk-delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  });
  return parseJson<{ deleted_count: number }>(response);
}

export async function fetchRuleConfig() {
  const response = await fetch('/api/admin/soil/rules', { cache: 'no-store' });
  return parseJson<{ rules: RuleConfig[]; templates: TemplateConfig[] }>(response);
}

export async function updateRuleConfig(payload: {
  rule_id?: string;
  rule_definition_json?: string;
  enabled?: boolean;
  template_id?: string;
  template_text?: string;
}) {
  const response = await fetch('/api/admin/soil/rules', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return parseJson<{ rules: RuleConfig[]; templates: TemplateConfig[] }>(response);
}
