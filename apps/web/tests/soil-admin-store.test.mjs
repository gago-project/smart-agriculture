import test from 'node:test';
import assert from 'node:assert/strict';

import {
  createDefaultAdminState,
  querySoilRecords,
  updateSoilRecordField,
  deleteSoilRecords,
  updateRuleDefinition,
  updateTemplateText,
} from '../lib/server/soilAdminStore.mjs';

test('querySoilRecords filters and paginates server-side', () => {
  const state = createDefaultAdminState();
  const result = querySoilRecords(state.records, {
    page: 1,
    page_size: 2,
    city_name: '南通市',
    soil_anomaly_type: 'normal',
  });

  assert.equal(result.page, 1);
  assert.equal(result.page_size, 2);
  assert.equal(result.rows.length, 2);
  assert.equal(result.total >= 2, true);
  assert.equal(result.rows.every((row) => row.city_name === '南通市'), true);
});

test('createDefaultAdminState mirrors current soil seed era and key devices', () => {
  const state = createDefaultAdminState();
  const recordIds = state.records.map((item) => item.device_sn);
  const sampleTimes = state.records.map((item) => item.sample_time);

  assert.equal(recordIds.includes('SNS00213807'), true);
  assert.equal(sampleTimes.every((item) => String(item).startsWith('2026-04-')), true);
});

test('updateSoilRecordField and deleteSoilRecords mutate selected records only', () => {
  const state = createDefaultAdminState();
  const first = state.records[0];
  const second = state.records[1];

  const updated = updateSoilRecordField(state.records, first.record_id, 'city_name', '南京市');
  assert.equal(updated.record.city_name, '南京市');
  assert.equal(updated.records.find((item) => item.record_id === second.record_id)?.city_name, second.city_name);

  const deleted = deleteSoilRecords(updated.records, [first.record_id]);
  assert.equal(deleted.deleted_count, 1);
  assert.equal(deleted.records.some((item) => item.record_id === first.record_id), false);
});

test('updateRuleDefinition and updateTemplateText keep admin config editable', () => {
  const state = createDefaultAdminState();
  const nextRule = updateRuleDefinition(state.rules, 'soil_warning_v1', '{"rules":[{"condition":"water20cm < 45"}]}', false);
  const nextTemplate = updateTemplateText(state.templates, 'soil_warning_template_v1', '告警：{{device_sn}} -> {{warning_level}}');

  assert.equal(nextRule.rule.enabled, false);
  assert.match(nextRule.rule.rule_definition_json, /water20cm < 45/);
  assert.match(nextTemplate.template.template_text, /warning_level/);
});
