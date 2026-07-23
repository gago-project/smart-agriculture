import crypto from 'node:crypto';

export const DEFAULT_SOIL_IMPORT_PREVIEW_PAGE_SIZE = 10;
export const SOIL_IMPORT_PREVIEW_TTL_MS = 30 * 60 * 1000;

const previewCache = new Map();

export class SoilImportPreviewCacheError extends Error {
  constructor(message, options = {}) {
    super(message);
    this.name = 'SoilImportPreviewCacheError';
    this.code = options.code || 'preview_not_found';
    this.status = options.status || 404;
  }
}

function nowMs() {
  return Date.now();
}

function toIsoString(timestampMs) {
  return new Date(timestampMs).toISOString();
}

function isExpired(entry, currentTimeMs = nowMs()) {
  return Number(entry?.expires_at_ms || 0) <= currentTimeMs;
}

function normalizeDiffRow(row, index) {
  return {
    diff_id: Number(row.diff_id || index + 1),
    diff_type: row.diff_type,
    id: row.id ?? null,
    source_row: row.source_row ?? null,
    db_record: row.db_record ?? row.db_record_json ?? null,
    import_record: row.import_record ?? row.import_record_json ?? null,
    field_changes: row.field_changes ?? row.field_changes_json ?? null,
  };
}

function pruneExpiredEntries(currentTimeMs = nowMs()) {
  for (const [token, entry] of previewCache.entries()) {
    if (isExpired(entry, currentTimeMs)) {
      previewCache.delete(token);
    }
  }
}

function previewNotFoundError() {
  return new SoilImportPreviewCacheError('预览已过期，请重新生成预览', {
    code: 'preview_expired',
    status: 410,
  });
}

export function createSoilImportPreviewEntry({
  filename,
  rawRows,
  invalidRows,
  importedRecords,
  summary,
  diffRows,
  ttlMs = SOIL_IMPORT_PREVIEW_TTL_MS,
}) {
  const currentTimeMs = nowMs();
  pruneExpiredEntries(currentTimeMs);

  const previewToken = crypto.randomUUID();
  const expiresAtMs = currentTimeMs + ttlMs;
  const normalizedDiffRows = (diffRows || []).map((row, index) => normalizeDiffRow(row, index));
  previewCache.set(previewToken, {
    preview_token: previewToken,
    filename,
    raw_rows: Number(rawRows || 0),
    invalid_rows: Number(invalidRows || 0),
    imported_records: importedRecords || [],
    summary: summary || null,
    diff_rows: normalizedDiffRows,
    created_at: toIsoString(currentTimeMs),
    created_at_ms: currentTimeMs,
    expires_at: toIsoString(expiresAtMs),
    expires_at_ms: expiresAtMs,
  });

  return {
    preview_token: previewToken,
    filename,
    summary: summary || null,
    expires_at: toIsoString(expiresAtMs),
  };
}

export function getSoilImportPreviewEntry(previewToken) {
  pruneExpiredEntries();
  const entry = previewCache.get(previewToken);
  if (!entry || isExpired(entry)) {
    previewCache.delete(previewToken);
    return null;
  }
  return entry;
}

export function expireSoilImportPreviewEntry(previewToken) {
  previewCache.delete(previewToken);
}

export function listSoilImportPreviewDiff(previewToken, query = {}) {
  const entry = getSoilImportPreviewEntry(previewToken);
  if (!entry) {
    throw previewNotFoundError();
  }

  const pageSize = DEFAULT_SOIL_IMPORT_PREVIEW_PAGE_SIZE;
  const page = Math.max(1, Number(query.page || 1));
  const diffType = String(query.type || 'all').trim() || 'all';
  const rows = diffType === 'all'
    ? entry.diff_rows
    : entry.diff_rows.filter((row) => row.diff_type === diffType);
  const total = rows.length;
  const totalPages = total === 0 ? 0 : Math.ceil(total / pageSize);
  const boundedPage = totalPages > 0 ? Math.min(page, totalPages) : 1;
  const start = (boundedPage - 1) * pageSize;

  return {
    rows: rows.slice(start, start + pageSize),
    total,
    page: boundedPage,
    page_size: pageSize,
    total_pages: totalPages,
    summary: entry.summary,
    filename: entry.filename,
    preview_token: entry.preview_token,
    expires_at: entry.expires_at,
  };
}
