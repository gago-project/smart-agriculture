import * as XLSX from 'xlsx';

import { normalizeRecord } from './soilAdminStore.mjs';

const SOURCE_ROW_META_KEY = '__source_row';

function excelSerialToDateString(serialValue) {
  const wholeDays = Math.floor(serialValue);
  const dayFraction = serialValue - wholeDays;
  const baseTime = Date.UTC(1899, 11, 30);
  const millis = wholeDays * 24 * 60 * 60 * 1000 + Math.round(dayFraction * 24 * 60 * 60 * 1000);
  const date = new Date(baseTime + millis);
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')} ${String(date.getUTCHours()).padStart(2, '0')}:${String(date.getUTCMinutes()).padStart(2, '0')}:${String(date.getUTCSeconds()).padStart(2, '0')}`;
}

function normalizeDate(value) {
  if (value === null || value === undefined || value === '') return '';
  if (value instanceof Date) {
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, '0');
    const day = String(value.getDate()).padStart(2, '0');
    const hour = String(value.getHours()).padStart(2, '0');
    const minute = String(value.getMinutes()).padStart(2, '0');
    const second = String(value.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}:${second}`;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    return excelSerialToDateString(value);
  }
  return String(value).trim();
}

function toNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function mapSoilRow(row, filename, sheetName, sourceRow) {
  const normalized = normalizeRecord({
    id: String(row.id || '').trim(),
    sn: String(row.sn || '').trim(),
    gatewayid: String(row.gatewayid || '').trim(),
    sensorid: String(row.sensorid || '').trim(),
    unitid: String(row.unitid || '').trim(),
    city: String(row.city || '').trim(),
    county: String(row.county || '').trim(),
    time: normalizeDate(row.time),
    create_time: normalizeDate(row.create_time),
    water20cm: toNumber(row.water20cm),
    water40cm: toNumber(row.water40cm),
    water60cm: toNumber(row.water60cm),
    water80cm: toNumber(row.water80cm),
    t20cm: toNumber(row.t20cm),
    t40cm: toNumber(row.t40cm),
    t60cm: toNumber(row.t60cm),
    t80cm: toNumber(row.t80cm),
    water20cmfieldstate: String(row.water20cmfieldstate || '').trim(),
    water40cmfieldstate: String(row.water40cmfieldstate || '').trim(),
    water60cmfieldstate: String(row.water60cmfieldstate || '').trim(),
    water80cmfieldstate: String(row.water80cmfieldstate || '').trim(),
    t20cmfieldstate: String(row.t20cmfieldstate || '').trim(),
    t40cmfieldstate: String(row.t40cmfieldstate || '').trim(),
    t60cmfieldstate: String(row.t60cmfieldstate || '').trim(),
    t80cmfieldstate: String(row.t80cmfieldstate || '').trim(),
    lat: toNumber(row.lat),
    lon: toNumber(row.lon),
  });
  Object.defineProperty(normalized, SOURCE_ROW_META_KEY, {
    value: sourceRow,
    enumerable: false,
    configurable: true,
    writable: false,
  });
  return normalized;
}

export function getRecordSourceRow(record) {
  const value = record?.[SOURCE_ROW_META_KEY];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export function parseSoilWorkbookBuffer(buffer, filename = 'soil.xlsx') {
  const workbook = XLSX.read(buffer, { type: 'buffer', cellDates: true });
  const firstSheetName = workbook.SheetNames[0];
  const firstSheet = workbook.Sheets[firstSheetName];
  const rows = XLSX.utils.sheet_to_json(firstSheet, { defval: null, raw: true });
  const validRecords = [];
  const invalidRows = [];

  for (const [index, row] of rows.entries()) {
    const mapped = mapSoilRow(row, filename, firstSheetName, index + 2);
    if (mapped.id && mapped.sn && mapped.create_time) {
      validRecords.push(mapped);
      continue;
    }
    invalidRows.push({
      source_row: index + 2,
      reason: '缺少 id、sn 或 create_time',
      record: mapped,
    });
  }

  return {
    filename,
    raw_rows: rows.length,
    loaded_rows: validRecords.length,
    records: validRecords,
    invalid_rows: invalidRows,
  };
}
