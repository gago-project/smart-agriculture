const SOIL_RECORD_SNAPSHOT_FIELDS = [
  'device_sn',
  'gateway_id',
  'sensor_id',
  'unit_id',
  'device_name',
  'city_name',
  'county_name',
  'town_name',
  'sample_time',
  'create_time',
  'water20cm',
  'water40cm',
  'water60cm',
  'water80cm',
  't20cm',
  't40cm',
  't60cm',
  't80cm',
  'water20cm_field_state',
  'water40cm_field_state',
  'water60cm_field_state',
  'water80cm_field_state',
  't20cm_field_state',
  't40cm_field_state',
  't60cm_field_state',
  't80cm_field_state',
  'soil_anomaly_type',
  'soil_anomaly_score',
  'longitude',
  'latitude',
  'source_file',
  'source_sheet',
  'source_row',
];

const SOIL_RECORD_COMPARE_FIELDS = SOIL_RECORD_SNAPSHOT_FIELDS.filter((field) =>
  !['source_file', 'source_sheet', 'source_row'].includes(field));

const NUMERIC_FIELDS = new Set([
  'water20cm',
  'water40cm',
  'water60cm',
  'water80cm',
  't20cm',
  't40cm',
  't60cm',
  't80cm',
  'soil_anomaly_score',
  'longitude',
  'latitude',
  'source_row',
]);

function normalizeComparableValue(field, value) {
  if (value === undefined || value === null || value === '') {
    return null;
  }
  if (NUMERIC_FIELDS.has(field)) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return String(value).trim();
}

export function snapshotSoilRecord(record) {
  return {
    record_id: String(record.record_id || '').trim() || null,
    ...Object.fromEntries(
      SOIL_RECORD_SNAPSHOT_FIELDS.map((field) => [field, normalizeComparableValue(field, record[field])]),
    ),
  };
}

export function buildSoilFieldChanges(currentRecord, nextRecord) {
  const changes = {};
  for (const field of SOIL_RECORD_COMPARE_FIELDS) {
    const before = normalizeComparableValue(field, currentRecord[field]);
    const after = normalizeComparableValue(field, nextRecord[field]);
    if (before !== after) {
      changes[field] = { before, after };
    }
  }
  return changes;
}

export function findDuplicateRecordIds(records) {
  const seen = new Map();
  for (const record of records) {
    const recordId = String(record.record_id || '').trim();
    if (!recordId) {
      continue;
    }
    const rows = seen.get(recordId) || [];
    rows.push(Number(record.source_row || 0));
    seen.set(recordId, rows);
  }
  return [...seen.entries()]
    .filter(([, rows]) => rows.length > 1)
    .map(([record_id, source_rows]) => ({ record_id, source_rows }));
}

export function getApplyRowsForMode(summary, mode) {
  if (mode === 'replace') {
    return Number(summary.valid_rows || 0);
  }
  return Number(summary.create_rows || 0);
}

export function buildSoilImportPreview({ existingRecords, importedRecords, invalidRows = [] }) {
  const duplicateRecordIds = findDuplicateRecordIds(importedRecords);
  if (duplicateRecordIds.length > 0) {
    return { duplicate_record_ids: duplicateRecordIds };
  }

  const summary = {
    raw_rows: importedRecords.length + invalidRows.length,
    valid_rows: importedRecords.length,
    invalid_rows: invalidRows.length,
    create_rows: 0,
    update_rows: 0,
    unchanged_rows: 0,
    delete_rows: 0,
    apply_rows: 0,
  };

  const diffRows = [];
  const existingByRecordId = new Map(existingRecords.map((record) => [record.record_id, record]));
  const importedRecordIds = new Set();

  for (const invalidRow of invalidRows) {
    diffRows.push({
      diff_type: 'invalid',
      record_id: invalidRow.record?.record_id || null,
      source_row: invalidRow.source_row || null,
      db_record_json: null,
      import_record_json: invalidRow.record ? snapshotSoilRecord(invalidRow.record) : null,
      field_changes_json: { reason: invalidRow.reason || '无效数据' },
    });
  }

  for (const importedRecord of importedRecords) {
    const importedSnapshot = snapshotSoilRecord(importedRecord);
    importedRecordIds.add(importedSnapshot.record_id);
    const existingRecord = existingByRecordId.get(importedSnapshot.record_id);
    if (!existingRecord) {
      summary.create_rows += 1;
      diffRows.push({
        diff_type: 'create',
        record_id: importedSnapshot.record_id,
        source_row: importedSnapshot.source_row,
        db_record_json: null,
        import_record_json: importedSnapshot,
        field_changes_json: null,
      });
      continue;
    }

    const existingSnapshot = snapshotSoilRecord(existingRecord);
    const fieldChanges = buildSoilFieldChanges(existingSnapshot, importedSnapshot);
    if (Object.keys(fieldChanges).length === 0) {
      summary.unchanged_rows += 1;
      diffRows.push({
        diff_type: 'unchanged',
        record_id: importedSnapshot.record_id,
        source_row: importedSnapshot.source_row,
        db_record_json: existingSnapshot,
        import_record_json: importedSnapshot,
        field_changes_json: null,
      });
      continue;
    }

    summary.update_rows += 1;
    diffRows.push({
      diff_type: 'update',
      record_id: importedSnapshot.record_id,
      source_row: importedSnapshot.source_row,
      db_record_json: existingSnapshot,
      import_record_json: importedSnapshot,
      field_changes_json: fieldChanges,
    });
  }

  for (const existingRecord of existingRecords) {
    if (importedRecordIds.has(existingRecord.record_id)) {
      continue;
    }
    summary.delete_rows += 1;
    diffRows.push({
      diff_type: 'delete',
      record_id: existingRecord.record_id,
      source_row: null,
      db_record_json: snapshotSoilRecord(existingRecord),
      import_record_json: null,
      field_changes_json: null,
    });
  }

  summary.apply_rows = getApplyRowsForMode(summary, 'incremental');
  return {
    summary,
    diff_rows: diffRows,
  };
}
