import test from 'node:test';
import assert from 'node:assert/strict';

import {
  buildSoilImportPreview,
  findDuplicateRecordIds,
  getApplyRowsForMode,
} from '../lib/server/soilImportJob.mjs';

test('findDuplicateRecordIds returns conflicting record ids with source rows', () => {
  const duplicates = findDuplicateRecordIds([
    { record_id: 'soil-1', source_row: 2 },
    { record_id: 'soil-2', source_row: 3 },
    { record_id: 'soil-1', source_row: 8 },
  ]);

  assert.deepEqual(duplicates, [
    { record_id: 'soil-1', source_rows: [2, 8] },
  ]);
});

test('buildSoilImportPreview classifies create update unchanged delete and invalid rows', () => {
  const preview = buildSoilImportPreview({
    existingRecords: [
      {
        record_id: 'keep-same',
        device_sn: 'SNS-1',
        city_name: '南京市',
        sample_time: '2026-04-20 00:00:00',
        water20cm: 30,
        source_file: 'old.xlsx',
        source_row: 2,
      },
      {
        record_id: 'need-update',
        device_sn: 'SNS-2',
        city_name: '苏州市',
        sample_time: '2026-04-20 00:00:00',
        water20cm: 40,
        source_file: 'old.xlsx',
        source_row: 3,
      },
      {
        record_id: 'missing-in-file',
        device_sn: 'SNS-3',
        city_name: '南通市',
        sample_time: '2026-04-20 00:00:00',
        water20cm: 50,
        source_file: 'old.xlsx',
        source_row: 4,
      },
    ],
    importedRecords: [
      {
        record_id: 'keep-same',
        device_sn: 'SNS-1',
        city_name: '南京市',
        sample_time: '2026-04-20 00:00:00',
        water20cm: 30,
        source_file: 'new.xlsx',
        source_row: 2,
      },
      {
        record_id: 'need-update',
        device_sn: 'SNS-2',
        city_name: '南京市',
        sample_time: '2026-04-20 00:00:00',
        water20cm: 45,
        source_file: 'new.xlsx',
        source_row: 3,
      },
      {
        record_id: 'brand-new',
        device_sn: 'SNS-4',
        city_name: '扬州市',
        sample_time: '2026-04-20 00:00:00',
        water20cm: 60,
        source_file: 'new.xlsx',
        source_row: 4,
      },
    ],
    invalidRows: [
      {
        source_row: 5,
        reason: '缺少 device_sn 或 sample_time',
        record: {
          record_id: 'invalid-1',
          device_sn: '',
          city_name: '镇江市',
          sample_time: '',
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
  assert.match(JSON.stringify(preview.diff_rows.find((item) => item.diff_type === 'update')?.field_changes_json), /南京市/);
});

test('buildSoilImportPreview stops on duplicate valid record ids', () => {
  const preview = buildSoilImportPreview({
    existingRecords: [],
    importedRecords: [
      { record_id: 'dup-1', source_row: 2 },
      { record_id: 'dup-1', source_row: 6 },
    ],
    invalidRows: [],
  });

  assert.deepEqual(preview.duplicate_record_ids, [
    { record_id: 'dup-1', source_rows: [2, 6] },
  ]);
});

test('getApplyRowsForMode keeps incremental as create-only', () => {
  const summary = {
    valid_rows: 10,
    create_rows: 3,
  };

  assert.equal(getApplyRowsForMode(summary, 'incremental'), 3);
  assert.equal(getApplyRowsForMode(summary, 'replace'), 10);
});
