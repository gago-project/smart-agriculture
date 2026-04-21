import crypto from 'node:crypto';
import * as XLSX from 'xlsx';

import { normalizeRecord } from './soilAdminStore.mjs';

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
  return String(value);
}

function toNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function mapSoilRow(row, filename, sheetName, sourceRow) {
  return normalizeRecord({
    record_id: String(row.id || crypto.randomUUID()),
    device_sn: String(row.sn || row.device_sn || '').trim(),
    gateway_id: String(row.gatewayid || row.gateway_id || '').trim(),
    sensor_id: String(row.sensorid || row.sensor_id || '').trim(),
    unit_id: String(row.unitid || row.unit_id || '').trim(),
    city_name: String(row.city || row.city_name || '').trim(),
    county_name: String(row.county || row.county_name || '').trim(),
    town_name: String(row.town || row.town_name || '').trim(),
    device_name: String(row.device_name || row.sn || '').trim(),
    sample_time: normalizeDate(row.time || row.sample_time || row.record_time || row.create_time),
    create_time: normalizeDate(row.create_time),
    water20cm: toNumber(row.water20cm),
    water40cm: toNumber(row.water40cm),
    water60cm: toNumber(row.water60cm),
    water80cm: toNumber(row.water80cm),
    t20cm: toNumber(row.t20cm),
    t40cm: toNumber(row.t40cm),
    t60cm: toNumber(row.t60cm),
    t80cm: toNumber(row.t80cm),
    water20cm_field_state: String(row.water20cmfieldstate || row.water20cm_field_state || '').trim(),
    water40cm_field_state: String(row.water40cmfieldstate || row.water40cm_field_state || '').trim(),
    water60cm_field_state: String(row.water60cmfieldstate || row.water60cm_field_state || '').trim(),
    water80cm_field_state: String(row.water80cmfieldstate || row.water80cm_field_state || '').trim(),
    t20cm_field_state: String(row.t20cmfieldstate || row.t20cm_field_state || '').trim(),
    t40cm_field_state: String(row.t40cmfieldstate || row.t40cm_field_state || '').trim(),
    t60cm_field_state: String(row.t60cmfieldstate || row.t60cm_field_state || '').trim(),
    t80cm_field_state: String(row.t80cmfieldstate || row.t80cm_field_state || '').trim(),
    latitude: toNumber(row.lat || row.latitude),
    longitude: toNumber(row.lon || row.longitude),
    source_file: filename,
    source_sheet: sheetName,
    source_row: sourceRow,
  });
}

export function parseSoilWorkbookBuffer(buffer, filename = 'soil.xlsx') {
  const workbook = XLSX.read(buffer, { type: 'buffer', cellDates: true });
  const firstSheetName = workbook.SheetNames[0];
  const firstSheet = workbook.Sheets[firstSheetName];
  const rows = XLSX.utils.sheet_to_json(firstSheet, { defval: null, raw: true });
  const records = rows
    .map((row, index) => mapSoilRow(row, filename, firstSheetName, index + 2))
    .filter((item) => item.device_sn && item.sample_time);

  return {
    filename,
    raw_rows: rows.length,
    loaded_rows: records.length,
    records,
  };
}
