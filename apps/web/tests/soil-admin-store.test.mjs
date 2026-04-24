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
    city: '南通市',
    create_time_from: '2026-04-01 00:00:00',
  });

  assert.equal(result.page, 1);
  assert.equal(result.page_size, 2);
  assert.equal(result.rows.length, 2);
  assert.equal(result.total >= 2, true);
  assert.equal(result.rows.every((row) => row.city === '南通市'), true);
});

test('createDefaultAdminState mirrors current soil seed era and key devices', () => {
  const state = createDefaultAdminState();
  const sns = state.records.map((item) => item.sn);
  const createTimes = state.records.map((item) => item.create_time);

  assert.equal(sns.includes('SNS00213807'), true);
  assert.equal(createTimes.every((item) => String(item).startsWith('2026-04-')), true);
});

test('updateSoilRecordField and deleteSoilRecords mutate selected records only', () => {
  const state = createDefaultAdminState();
  const first = state.records[0];
  const second = state.records[1];

  const updated = updateSoilRecordField(state.records, first.id, 'city', '南京市');
  assert.equal(updated.record.city, '南京市');
  assert.equal(updated.records.find((item) => item.id === second.id)?.city, second.city);

  const deleted = deleteSoilRecords(updated.records, [first.id]);
  assert.equal(deleted.deleted_count, 1);
  assert.equal(deleted.records.some((item) => item.id === first.id), false);
});

test('updateRuleDefinition and updateTemplateText keep admin config editable', () => {
  const state = createDefaultAdminState();
  const nextRule = updateRuleDefinition(state.rules, 'soil_warning_v1', '{"rules":[{"condition":"water20cm < 45"}]}', false);
  const nextTemplate = updateTemplateText(state.templates, 'soil_warning_template_v1', '告警：{{sn}} -> {{warning_level}}');

  assert.equal(nextRule.rule.enabled, false);
  assert.match(nextRule.rule.rule_definition_json, /water20cm < 45/);
  assert.match(nextTemplate.template.template_text, /warning_level/);
});
