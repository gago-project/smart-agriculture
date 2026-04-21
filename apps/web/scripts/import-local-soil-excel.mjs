import crypto from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { basename, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { withMysqlConnection } from '../lib/server/mysql.mjs';
import { buildRegionAliasRows, upsertRegionAliasRows } from '../lib/server/regionAliasSeed.mjs';
import { parseSoilWorkbookBuffer } from '../lib/server/soilImport.mjs';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(scriptDir, '../../..');
const defaultExcelPath = resolve(repoRoot, 'infra/mysql/local/soil_data.local.xlsx');
const chunkSize = Math.max(100, Number(process.env.SOIL_IMPORT_CHUNK_SIZE || '500'));

const factColumns = [
  'record_id',
  'batch_id',
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

function normalizePath(pathValue) {
  if (!pathValue) {
    return '';
  }
  if (pathValue.startsWith('/')) {
    return pathValue;
  }
  return resolve(repoRoot, pathValue);
}

function resolveExcelSource() {
  const configured = String(process.env.SOIL_EXCEL_SOURCE || '').trim();
  if (configured) {
    return normalizePath(configured);
  }
  if (existsSync(defaultExcelPath)) {
    return defaultExcelPath;
  }
  throw new Error('未找到 SOIL_EXCEL_SOURCE，也未检测到 infra/mysql/local/soil_data.local.xlsx');
}

function nullableString(value) {
  const normalized = String(value ?? '').trim();
  return normalized ? normalized : null;
}

function nullableNumber(value) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function toFactRow(record, batchId, filename) {
  return [
    nullableString(record.record_id) || crypto.randomUUID(),
    batchId,
    nullableString(record.device_sn),
    nullableString(record.gateway_id),
    nullableString(record.sensor_id),
    nullableString(record.unit_id),
    nullableString(record.device_name),
    nullableString(record.city_name),
    nullableString(record.county_name),
    nullableString(record.town_name),
    nullableString(record.sample_time),
    nullableString(record.create_time || record.sample_time),
    nullableNumber(record.water20cm),
    nullableNumber(record.water40cm),
    nullableNumber(record.water60cm),
    nullableNumber(record.water80cm),
    nullableNumber(record.t20cm),
    nullableNumber(record.t40cm),
    nullableNumber(record.t60cm),
    nullableNumber(record.t80cm),
    nullableString(record.water20cm_field_state),
    nullableString(record.water40cm_field_state),
    nullableString(record.water60cm_field_state),
    nullableString(record.water80cm_field_state),
    nullableString(record.t20cm_field_state),
    nullableString(record.t40cm_field_state),
    nullableString(record.t60cm_field_state),
    nullableString(record.t80cm_field_state),
    nullableString(record.soil_anomaly_type),
    nullableNumber(record.soil_anomaly_score),
    nullableNumber(record.longitude),
    nullableNumber(record.latitude),
    filename,
    nullableString(record.source_sheet),
    record.source_row ? Number(record.source_row) : null,
  ];
}

function chunk(items, size) {
  const output = [];
  for (let index = 0; index < items.length; index += size) {
    output.push(items.slice(index, index + size));
  }
  return output;
}

async function insertFactChunk(connection, rows) {
  const placeholders = rows.map(() => `(${factColumns.map(() => '?').join(', ')})`).join(', ');
  const values = rows.flat();
  const updateAssignments = factColumns
    .filter((column) => column !== 'record_id')
    .map((column) => `${column} = VALUES(${column})`)
    .join(',\n            ');

  await connection.execute(
    `INSERT INTO fact_soil_moisture (
      ${factColumns.join(', ')}
    ) VALUES ${placeholders}
    ON DUPLICATE KEY UPDATE
            ${updateAssignments}`,
    values,
  );
}

async function main() {
  const sourcePath = resolveExcelSource();
  if (!existsSync(sourcePath)) {
    throw new Error(`土壤墒情 Excel 不存在：${sourcePath}`);
  }

  const filename = basename(sourcePath);
  const workbookBuffer = readFileSync(sourcePath);
  const parsed = parseSoilWorkbookBuffer(workbookBuffer, filename);

  if (parsed.records.length === 0) {
    throw new Error(`Excel 中没有可导入的有效墒情记录：${filename}`);
  }

  const batchId = crypto.randomUUID();
  const sourceName = 'local_excel_import';
  const batchNote = 'Loaded from local Excel source via apps/web/scripts/import-local-soil-excel.mjs';
  let loadedRows = 0;
  let aliasRows = 0;

  await withMysqlConnection(async (connection) => {
    await connection.execute(
      `INSERT INTO etl_import_batch (
         batch_id, source_name, source_file, started_at, finished_at, status, raw_row_count, loaded_row_count, note
       ) VALUES (?, ?, ?, NOW(), NULL, 'processing', ?, 0, ?)`,
      [batchId, sourceName, filename, parsed.raw_rows, batchNote],
    );

    try {
      await connection.beginTransaction();
      await connection.execute('DELETE FROM fact_soil_moisture WHERE source_file = ?', [filename]);
      for (const recordChunk of chunk(parsed.records, chunkSize)) {
        const chunkRows = recordChunk.map((record) => toFactRow(record, batchId, filename));
        await insertFactChunk(connection, chunkRows);
        loadedRows += recordChunk.length;
      }
      await connection.commit();
      await connection.execute(
        `UPDATE etl_import_batch
         SET finished_at = NOW(), status = 'success', loaded_row_count = ?, note = ?
         WHERE batch_id = ?`,
        [loadedRows, batchNote, batchId],
      );
      aliasRows = await upsertRegionAliasRows(connection, buildRegionAliasRows(parsed.records));
    } catch (error) {
      try {
        await connection.rollback();
      } catch {
      }
      await connection.execute(
        `UPDATE etl_import_batch
         SET finished_at = NOW(), status = 'failed', loaded_row_count = ?, note = ?
         WHERE batch_id = ?`,
        [loadedRows, error instanceof Error ? error.message.slice(0, 500) : 'excel import failed', batchId],
      );
      throw error;
    }
  });

  console.log(
    JSON.stringify({
      batch_id: batchId,
      filename,
      raw_rows: parsed.raw_rows,
      loaded_rows: loadedRows,
      region_alias_rows: aliasRows,
      source: process.env.SOIL_EXCEL_SOURCE ? 'SOIL_EXCEL_SOURCE' : 'infra/mysql/local/soil_data.local.xlsx',
    }),
  );
}

await main();
