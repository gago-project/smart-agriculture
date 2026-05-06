import test from 'node:test';
import assert from 'node:assert/strict';

async function loadPreviewModule() {
  return import(new URL(`../lib/server/soilImportPreview.mjs?ts=${Date.now()}`, import.meta.url));
}

test('buildSoilImportPreview classifies create update unchanged delete and invalid rows', async () => {
  const { buildSoilImportPreview } = await loadPreviewModule();

  const preview = buildSoilImportPreview({
    existingRecords: [
      {
        id: 'keep-same',
        sn: 'SNS-1',
        city: '南京市',
        create_time: '2026-04-20 00:00:00',
        water20cm: 30,
        source_row: 2,
      },
      {
        id: 'need-update',
        sn: 'SNS-2',
        city: '苏州市',
        create_time: '2026-04-20 00:00:00',
        water20cm: 40,
        source_row: 3,
      },
      {
        id: 'missing-in-file',
        sn: 'SNS-3',
        city: '南通市',
        create_time: '2026-04-20 00:00:00',
        water20cm: 50,
        source_row: 4,
      },
    ],
    importedRecords: [
      {
        id: 'keep-same',
        sn: 'SNS-1',
        city: '南京市',
        create_time: '2026-04-20 00:00:00',
        water20cm: 30,
        source_row: 2,
      },
      {
        id: 'need-update',
        sn: 'SNS-2',
        city: '南京市',
        create_time: '2026-04-20 00:00:00',
        water20cm: 45,
        source_row: 3,
      },
      {
        id: 'brand-new',
        sn: 'SNS-4',
        city: '扬州市',
        create_time: '2026-04-20 00:00:00',
        water20cm: 60,
        source_row: 4,
      },
    ],
    invalidRows: [
      {
        source_row: 5,
        reason: '缺少 id、sn 或 create_time',
        record: {
          id: 'invalid-1',
          sn: '',
          city: '镇江市',
          create_time: '',
          source_row: 5,
        },
      },
    ],
  });

  assert.equal(preview.summary.raw_rows, 4);
  assert.equal(preview.summary.valid_rows, 3);
  assert.equal(preview.summary.invalid_rows, 1);
  assert.equal(preview.summary.create_rows, 1);
  assert.equal(preview.summary.update_rows, 1);
  assert.equal(preview.summary.unchanged_rows, 1);
  assert.equal(preview.summary.delete_rows, 1);
  assert.equal(preview.summary.apply_rows, 1);
  assert.deepEqual(
    preview.diff_rows.map((item) => item.diff_type),
    ['invalid', 'unchanged', 'update', 'create', 'delete'],
  );
});

test('buildSoilImportPreview stops on duplicate valid ids', async () => {
  const { buildSoilImportPreview } = await loadPreviewModule();

  const preview = buildSoilImportPreview({
    existingRecords: [],
    importedRecords: [
      { id: 'dup-1', source_row: 2 },
      { id: 'dup-1', source_row: 6 },
    ],
    invalidRows: [],
  });

  assert.deepEqual(preview.duplicate_ids, [
    { id: 'dup-1', source_rows: [2, 6] },
  ]);
});
