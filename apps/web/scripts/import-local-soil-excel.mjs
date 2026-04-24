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
  'id',
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

function chunk(items, size) {
  const output = [];
  for (let index = 0; index < items.length; index += size) {
    output.push(items.slice(index, index + size));
  }
  return output;
}

function toFactRow(record, filename) {
  return [
    record.id,
    record.sn || null,
    record.gatewayid || null,
    record.sensorid || null,
    record.unitid || null,
    record.city || null,
    record.county || null,
    record.time || null,
    record.create_time || null,
    record.water20cm ?? null,
    record.water40cm ?? null,
    record.water60cm ?? null,
    record.water80cm ?? null,
    record.t20cm ?? null,
    record.t40cm ?? null,
    record.t60cm ?? null,
    record.t80cm ?? null,
    record.water20cmfieldstate || null,
    record.water40cmfieldstate || null,
    record.water60cmfieldstate || null,
    record.water80cmfieldstate || null,
    record.t20cmfieldstate || null,
    record.t40cmfieldstate || null,
    record.t60cmfieldstate || null,
    record.t80cmfieldstate || null,
    record.lat ?? null,
    record.lon ?? null,
    filename,
    record.source_sheet || null,
    record.source_row ?? null,
  ];
}

async function insertFactChunk(connection, rows) {
  const placeholders = rows.map(() => `(${factColumns.map(() => '?').join(', ')})`).join(', ');
  const values = rows.flat();
  const updateAssignments = factColumns
    .filter((column) => column !== 'id')
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

  let loadedRows = 0;
  let aliasRows = 0;

  await withMysqlConnection(async (connection) => {
    await connection.beginTransaction();
    try {
      await connection.execute('DELETE FROM fact_soil_moisture WHERE source_file = ?', [filename]);
      for (const recordChunk of chunk(parsed.records, chunkSize)) {
        const chunkRows = recordChunk.map((record) => toFactRow(record, filename));
        await insertFactChunk(connection, chunkRows);
        loadedRows += recordChunk.length;
      }
      aliasRows = await upsertRegionAliasRows(connection, buildRegionAliasRows(parsed.records));
      await connection.commit();
    } catch (error) {
      try {
        await connection.rollback();
      } catch {
      }
      throw error;
    }
  });

  console.log(
    JSON.stringify({
      filename,
      raw_rows: parsed.raw_rows,
      loaded_rows: loadedRows,
      region_alias_rows: aliasRows,
      source: process.env.SOIL_EXCEL_SOURCE ? 'SOIL_EXCEL_SOURCE' : 'infra/mysql/local/soil_data.local.xlsx',
    }),
  );
}

await main();
