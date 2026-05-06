import test from 'node:test';
import assert from 'node:assert/strict';

const previewModuleUrl = new URL(`../lib/server/soilImportPreviewCache.mjs?ts=${Date.now()}`, import.meta.url);

test('createSoilImportPreview stores preview in memory and paginates diff rows at 10 per page', async () => {
  const {
    createSoilImportPreviewEntry,
    listSoilImportPreviewDiff,
  } = await import(previewModuleUrl);

  const preview = createSoilImportPreviewEntry({
    filename: 'soil.xlsx',
    rawRows: 12,
    invalidRows: 1,
    importedRecords: [{ id: 'soil-1' }],
    summary: {
      raw_rows: 12,
      valid_rows: 11,
      invalid_rows: 1,
      create_rows: 3,
      update_rows: 4,
      unchanged_rows: 2,
      delete_rows: 2,
      apply_rows: 3,
    },
    diffRows: Array.from({ length: 12 }, (_, index) => ({
      diff_id: index + 1,
      diff_type: index % 2 === 0 ? 'create' : 'update',
      id: `soil-${index + 1}`,
      source_row: index + 2,
      db_record: null,
      import_record: { id: `soil-${index + 1}` },
      field_changes: null,
    })),
  });

  assert.match(preview.preview_token, /^[a-f0-9-]{20,}$/i);
  assert.equal(preview.summary.update_rows, 4);

  const page1 = listSoilImportPreviewDiff(preview.preview_token, { type: 'all', page: 1, pageSize: 10 });
  assert.equal(page1.page_size, 10);
  assert.equal(page1.page, 1);
  assert.equal(page1.total, 12);
  assert.equal(page1.total_pages, 2);
  assert.equal(page1.rows.length, 10);
  assert.equal(page1.rows[0].diff_id, 1);

  const updateOnly = listSoilImportPreviewDiff(preview.preview_token, { type: 'update', page: 1, pageSize: 10 });
  assert.equal(updateOnly.total, 6);
  assert.ok(updateOnly.rows.every((row) => row.diff_type === 'update'));
});

test('soil import preview cache expires tokens explicitly', async () => {
  const {
    createSoilImportPreviewEntry,
    expireSoilImportPreviewEntry,
    getSoilImportPreviewEntry,
  } = await import(previewModuleUrl);

  const preview = createSoilImportPreviewEntry({
    filename: 'soil.xlsx',
    rawRows: 1,
    invalidRows: 0,
    importedRecords: [{ id: 'soil-1' }],
    summary: {
      raw_rows: 1,
      valid_rows: 1,
      invalid_rows: 0,
      create_rows: 1,
      update_rows: 0,
      unchanged_rows: 0,
      delete_rows: 0,
      apply_rows: 1,
    },
    diffRows: [],
  });

  assert.equal(getSoilImportPreviewEntry(preview.preview_token)?.filename, 'soil.xlsx');
  expireSoilImportPreviewEntry(preview.preview_token);
  assert.equal(getSoilImportPreviewEntry(preview.preview_token), null);
});
