const SOIL_RECORD_SNAPSHOT_FIELDS = [
  'sn',
  'gatewayid',
  'sensorid',
  'unitid',
  'city',
  'county',
  'time',
  'create_time',
  'water20cm',
  'water40cm',
  'water60cm',
  'water80cm',
  't20cm',
  't40cm',
  't60cm',
  't80cm',
  'water20cmfieldstate',
  'water40cmfieldstate',
  'water60cmfieldstate',
  'water80cmfieldstate',
  't20cmfieldstate',
  't40cmfieldstate',
  't60cmfieldstate',
  't80cmfieldstate',
  'lat',
  'lon',
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
  'lat',
  'lon',
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
    id: String(record.id || '').trim() || null,
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
    const recordId = String(record.id || '').trim();
    if (!recordId) {
      continue;
    }
    const rows = seen.get(recordId) || [];
    rows.push(Number(record.source_row || 0));
    seen.set(recordId, rows);
  }
  return [...seen.entries()]
    .filter(([, rows]) => rows.length > 1)
    .map(([id, source_rows]) => ({ id, source_rows }));
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
    return { duplicate_ids: duplicateRecordIds };
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
  const existingById = new Map(existingRecords.map((record) => [record.id, record]));
  const importedIds = new Set();

  for (const invalidRow of invalidRows) {
    diffRows.push({
      diff_type: 'invalid',
      id: invalidRow.record?.id || null,
      source_row: invalidRow.source_row || null,
      db_record_json: null,
      import_record_json: invalidRow.record ? snapshotSoilRecord(invalidRow.record) : null,
      field_changes_json: { reason: invalidRow.reason || '无效数据' },
    });
  }

  for (const importedRecord of importedRecords) {
    const importedSnapshot = snapshotSoilRecord(importedRecord);
    importedIds.add(importedSnapshot.id);
    const existingRecord = existingById.get(importedSnapshot.id);
    if (!existingRecord) {
      summary.create_rows += 1;
      diffRows.push({
        diff_type: 'create',
        id: importedSnapshot.id,
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
        id: importedSnapshot.id,
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
      id: importedSnapshot.id,
      source_row: importedSnapshot.source_row,
      db_record_json: existingSnapshot,
      import_record_json: importedSnapshot,
      field_changes_json: fieldChanges,
    });
  }

  for (const existingRecord of existingRecords) {
    if (importedIds.has(existingRecord.id)) {
      continue;
    }
    summary.delete_rows += 1;
    diffRows.push({
      diff_type: 'delete',
      id: existingRecord.id,
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
