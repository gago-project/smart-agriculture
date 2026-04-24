import test from 'node:test';
import assert from 'node:assert/strict';
import * as XLSX from 'xlsx';

import { parseSoilWorkbookBuffer } from '../lib/server/soilImport.mjs';

const EXPECTED_RECORD_KEYS = [
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
].sort();

test('parseSoilWorkbookBuffer keeps raw excel field contract', () => {
  const rows = [
    {
      id: 'record-1',
      sn: 'SNS90000001',
      time: '2026-04-21 00:00:00',
      water20cm: 41.2,
      water40cm: 52.1,
      water60cm: 63.3,
      water80cm: 74.4,
      t20cm: 18.5,
      t40cm: 17.8,
      t60cm: 17.2,
      t80cm: 16.6,
      lat: 32.11,
      lon: 118.88,
      city: '南京市',
      county: '江宁区',
      create_time: '2026-04-21 00:00:00',
    },
  ];
  const workbook = XLSX.utils.book_new();
  const worksheet = XLSX.utils.json_to_sheet(rows);
  XLSX.utils.book_append_sheet(workbook, worksheet, 'soil');
  const buffer = XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' });

  const parsed = parseSoilWorkbookBuffer(buffer, 'soil.xlsx');

  assert.equal(parsed.raw_rows, 1);
  assert.equal(parsed.records.length, 1);
  assert.equal(parsed.records[0].id, 'record-1');
  assert.equal(parsed.records[0].sn, 'SNS90000001');
  assert.equal(parsed.records[0].city, '南京市');
  assert.equal(parsed.records[0].county, '江宁区');
  assert.equal(parsed.records[0].time, '2026-04-21 00:00:00');
  assert.equal(parsed.records[0].create_time, '2026-04-21 00:00:00');
  assert.equal(parsed.records[0].source_file, 'soil.xlsx');
  assert.equal(parsed.records[0].source_sheet, 'soil');
  assert.equal(parsed.records[0].source_row, 2);
  assert.deepEqual(Object.keys(parsed.records[0]).sort(), EXPECTED_RECORD_KEYS);
});

test('parseSoilWorkbookBuffer converts excel serial datetime and keeps source ids', () => {
  const rows = [
    {
      id: 'record-serial-1',
      sn: 'SNS90000002',
      gatewayid: 'GW-1',
      sensorid: 'SE-1',
      unitid: 'UNIT-1',
      time: 45809,
      create_time: 45809,
      water20cm: 55.5,
      t20cm: 18.2,
      city: '苏州市',
      county: '昆山市',
    },
  ];
  const workbook = XLSX.utils.book_new();
  const worksheet = XLSX.utils.json_to_sheet(rows);
  XLSX.utils.book_append_sheet(workbook, worksheet, 'soil');
  const buffer = XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' });

  const parsed = parseSoilWorkbookBuffer(buffer, 'soil.xlsx');

  assert.equal(parsed.records.length, 1);
  assert.equal(parsed.records[0].id, 'record-serial-1');
  assert.equal(parsed.records[0].gatewayid, 'GW-1');
  assert.equal(parsed.records[0].sensorid, 'SE-1');
  assert.equal(parsed.records[0].unitid, 'UNIT-1');
  assert.equal(parsed.records[0].time, '2025-06-01 00:00:00');
  assert.equal(parsed.records[0].create_time, '2025-06-01 00:00:00');
});
