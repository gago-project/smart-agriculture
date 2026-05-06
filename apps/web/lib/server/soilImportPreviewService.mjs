import { applySoilImportRecords, listSoilFactSnapshots } from './soilAdminRepository.mjs';
import { buildSoilImportPreview } from './soilImportPreview.mjs';
import {
  DEFAULT_SOIL_IMPORT_PREVIEW_PAGE_SIZE,
  SoilImportPreviewCacheError,
  createSoilImportPreviewEntry,
  getSoilImportPreviewEntry,
  listSoilImportPreviewDiff,
} from './soilImportPreviewCache.mjs';
import { parseSoilWorkbookBuffer } from './soilImport.mjs';

function formatDuplicateIdMessage(duplicateIds) {
  return duplicateIds
    .map((item) => `${item.id} [${item.source_rows.join(', ')}]`)
    .join('；');
}

export async function createSoilImportPreview({ filename, contentBase64 }) {
  const buffer = Buffer.from(contentBase64, 'base64');
  const parsed = parseSoilWorkbookBuffer(buffer, filename);
  const existingRecords = await listSoilFactSnapshots();
  const preview = buildSoilImportPreview({
    existingRecords,
    importedRecords: parsed.records,
    invalidRows: parsed.invalid_rows,
  });

  if (preview.duplicate_ids?.length) {
    throw new Error(`上传文件中存在重复 id：${formatDuplicateIdMessage(preview.duplicate_ids)}`);
  }

  const diffRows = (preview.diff_rows || []).map((row, index) => ({
    diff_id: index + 1,
    diff_type: row.diff_type,
    id: row.id ?? null,
    source_row: row.source_row ?? null,
    db_record: row.db_record_json ?? null,
    import_record: row.import_record_json ?? null,
    field_changes: row.field_changes_json ?? null,
  }));

  return createSoilImportPreviewEntry({
    filename,
    rawRows: parsed.raw_rows,
    invalidRows: parsed.invalid_rows?.length ?? 0,
    importedRecords: parsed.records,
    summary: preview.summary,
    diffRows,
  });
}

export async function listSoilImportPreviewDiffPage(previewToken, query = {}) {
  return listSoilImportPreviewDiff(previewToken, {
    type: query.type || 'all',
    page: query.page || 1,
    pageSize: DEFAULT_SOIL_IMPORT_PREVIEW_PAGE_SIZE,
  });
}

export async function applySoilImportPreview({ previewToken, mode, confirmFullReplace }) {
  const entry = getSoilImportPreviewEntry(previewToken);
  if (!entry) {
    throw new SoilImportPreviewCacheError('预览已过期，请重新生成预览', {
      code: 'preview_expired',
      status: 410,
    });
  }

  const records = mode === 'replace'
    ? entry.imported_records
    : entry.diff_rows
      .filter((row) => row.diff_type === 'create' && row.import_record)
      .map((row) => row.import_record);

  return await applySoilImportRecords({
    filename: entry.filename,
    records,
    rawRows: entry.raw_rows,
    invalidRowsCount: entry.invalid_rows,
    mode,
    confirmFullReplace,
  });
}
