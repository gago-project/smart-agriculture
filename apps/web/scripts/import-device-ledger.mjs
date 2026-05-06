import { existsSync, readFileSync } from 'node:fs';
import { basename, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import * as XLSX from 'xlsx';

import { withMysqlConnection } from '../lib/server/mysql.mjs';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(scriptDir, '../../..');
const defaultExcelPath = resolve(repoRoot, 'infra/mysql/local/device_ledger.local.xlsx');
const chunkSize = Math.max(100, Number(process.env.DEVICE_LEDGER_CHUNK_SIZE || '500'));

const deviceColumns = [
  'id',
  'device_name',
  'region_code',
  'region_name',
  'lat',
  'lon',
  'sn',
  'type',
  'create_time',
  'p_id',
  'brand',
  'device_model',
  'agreement',
  'legal_person',
  'contact_information',
  'address',
  'insect_type',
  'city',
  'county',
  'tag',
];

function normalizePath(pathValue) {
  if (!pathValue) return '';
  if (pathValue.startsWith('/')) return pathValue;
  return resolve(repoRoot, pathValue);
}

function resolveExcelSource() {
  const configured = String(process.env.DEVICE_LEDGER_EXCEL_SOURCE || '').trim();
  if (configured) return normalizePath(configured);
  if (existsSync(defaultExcelPath)) return defaultExcelPath;
  throw new Error(
    '未找到设备台账 Excel。请将文件放到 infra/mysql/local/device_ledger.local.xlsx，' +
    '或通过环境变量 DEVICE_LEDGER_EXCEL_SOURCE 指定路径。',
  );
}

function normalizeDate(value) {
  if (value === null || value === undefined || value === '') return null;
  if (value instanceof Date) {
    const y = value.getFullYear();
    const mo = String(value.getMonth() + 1).padStart(2, '0');
    const d = String(value.getDate()).padStart(2, '0');
    const h = String(value.getHours()).padStart(2, '0');
    const mi = String(value.getMinutes()).padStart(2, '0');
    const s = String(value.getSeconds()).padStart(2, '0');
    return `${y}-${mo}-${d} ${h}:${mi}:${s}`;
  }
  const str = String(value).trim();
  return str || null;
}

function parseWorkbook(buffer) {
  const workbook = XLSX.read(buffer, { type: 'buffer', cellDates: true });
  const sheetName = workbook.SheetNames.find((n) => n === 'subject_device_record') ?? workbook.SheetNames[0];
  if (!sheetName) throw new Error('Excel 中未找到工作表');
  const sheet = workbook.Sheets[sheetName];
  const rows = XLSX.utils.sheet_to_json(sheet, { defval: null });
  if (rows.length === 0) throw new Error('Excel 工作表中没有数据行');
  return rows;
}

function toDeviceRow(record) {
  return [
    record.id ? String(record.id).trim() : null,
    record.device_name ? String(record.device_name).trim() : null,
    record.region_code ? String(record.region_code).trim() : null,
    record.region_name ? String(record.region_name).trim() : null,
    record.lat !== null && record.lat !== undefined ? String(record.lat).trim() : null,
    record.lon !== null && record.lon !== undefined ? String(record.lon).trim() : null,
    record.sn ? String(record.sn).trim() : null,
    record.type ? String(record.type).trim() : null,
    normalizeDate(record.create_time),
    record.p_id ? String(record.p_id).trim() : null,
    record.brand ? String(record.brand).trim() : null,
    record.device_model ? String(record.device_model).trim() : null,
    record.agreement ? String(record.agreement).trim() : null,
    record.legal_person ? String(record.legal_person).trim() : null,
    record.contact_information ? String(record.contact_information).trim() : null,
    record.address ? String(record.address).trim() : null,
    record.insect_type ? String(record.insect_type).trim() : null,
    record.city ? String(record.city).trim() : null,
    record.county ? String(record.county).trim() : null,
    record.tag ? String(record.tag).trim() : null,
  ];
}

function chunk(items, size) {
  const output = [];
  for (let i = 0; i < items.length; i += size) {
    output.push(items.slice(i, i + size));
  }
  return output;
}

async function insertChunk(connection, rows) {
  const placeholders = rows.map(() => `(${deviceColumns.map(() => '?').join(', ')})`).join(', ');
  const values = rows.flat();
  const updateAssignments = deviceColumns
    .filter((c) => c !== 'id')
    .map((c) => `${c} = VALUES(${c})`)
    .join(',\n            ');

  await connection.execute(
    `INSERT INTO subject_device_record (
      ${deviceColumns.join(', ')}
    ) VALUES ${placeholders}
    ON DUPLICATE KEY UPDATE
            ${updateAssignments}`,
    values,
  );
}

async function main() {
  const sourcePath = resolveExcelSource();
  if (!existsSync(sourcePath)) {
    throw new Error(`设备台账 Excel 不存在：${sourcePath}`);
  }

  const filename = basename(sourcePath);
  const buffer = readFileSync(sourcePath);
  const rows = parseWorkbook(buffer);

  const validRows = rows.filter((r) => r.id);
  if (validRows.length === 0) {
    throw new Error(`Excel 中没有带 id 字段的有效行：${filename}`);
  }

  let loadedRows = 0;

  await withMysqlConnection(async (connection) => {
    await connection.beginTransaction();
    try {
      for (const recordChunk of chunk(validRows, chunkSize)) {
        const chunkRows = recordChunk.map((record) => toDeviceRow(record));
        await insertChunk(connection, chunkRows);
        loadedRows += recordChunk.length;
      }
      await connection.commit();
    } catch (error) {
      try { await connection.rollback(); } catch { }
      throw error;
    }
  });

  const typeCounts = {};
  for (const row of validRows) {
    const t = row.type ? String(row.type).trim() : '(未知)';
    typeCounts[t] = (typeCounts[t] ?? 0) + 1;
  }

  console.log(
    JSON.stringify({
      filename,
      raw_rows: rows.length,
      loaded_rows: loadedRows,
      skipped_rows: rows.length - validRows.length,
      type_distribution: typeCounts,
      source: process.env.DEVICE_LEDGER_EXCEL_SOURCE
        ? 'DEVICE_LEDGER_EXCEL_SOURCE'
        : 'infra/mysql/local/device_ledger.local.xlsx',
    }),
  );
}

main().catch((error) => {
  console.error('设备台账导入失败:', error.message);
  process.exit(1);
});
