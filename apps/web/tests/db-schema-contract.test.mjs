import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const sql = fs.readFileSync(new URL('../../../infra/mysql/init/001_init_tables.sql', import.meta.url), 'utf8');

function extractTableBlock(tableName) {
  const match = sql.match(new RegExp(`CREATE TABLE IF NOT EXISTS ${tableName} \\(([\\s\\S]*?)\\n\\);`, 'i'));
  assert.ok(match, `missing table block for ${tableName}`);
  return match[1];
}

function extractColumns(tableName) {
  return extractTableBlock(tableName)
    .split('\n')
    .map((line) => line.trim().replace(/,$/, ''))
    .filter((line) => /^[a-z]/.test(line))
    .map((line) => line.match(/^`?([a-z0-9_]+)`?\s+/i)?.[1])
    .filter(Boolean);
}

test('mysql core tables strictly follow current soil domain contract', () => {
  for (const table of [
    'fact_soil_moisture',
    'soil_import_job',
    'soil_import_job_diff',
    'metric_rule',
    'admin_change_log',
    'warning_template',
    'region_alias',
    'agent_result_snapshot',
    'agent_result_snapshot_item',
    'agent_query_log',
    'auth_user',
    'auth_session',
  ]) {
    assert.match(sql, new RegExp(`CREATE TABLE IF NOT EXISTS ${table}\\b`));
  }
  assert.doesNotMatch(sql, /CREATE TABLE IF NOT EXISTS agent_chat_session\b/i);
  assert.doesNotMatch(sql, /CREATE TABLE IF NOT EXISTS agent_chat_turn\b/i);
  assert.match(sql, /DROP TABLE IF EXISTS agent_chat_turn;/i);
  assert.match(sql, /DROP TABLE IF EXISTS agent_chat_session;/i);
});

test('fact_soil_moisture columns exactly match raw excel contract', () => {
  assert.deepEqual(extractColumns('fact_soil_moisture'), [
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
  ]);
  assert.match(sql, /CREATE INDEX idx_soil_create_time ON fact_soil_moisture \(create_time\)/i);
  assert.match(sql, /CREATE INDEX idx_soil_sn_create_time ON fact_soil_moisture \(sn, create_time\)/i);
  assert.match(sql, /CREATE INDEX idx_soil_region_create_time ON fact_soil_moisture \(city, county, create_time\)/i);
});

test('soil import preview tables keep current job and diff fields', () => {
  assert.deepEqual(extractColumns('soil_import_job'), [
    'job_id',
    'filename',
    'requested_by_user_id',
    'requested_by_username',
    'status',
    'apply_mode',
    'processed_rows',
    'total_rows',
    'summary_json',
    'error_message',
    'finished_at',
    'created_at',
    'updated_at',
  ]);
  assert.deepEqual(extractColumns('soil_import_job_diff'), [
    'diff_id',
    'job_id',
    'diff_type',
    'id',
    'source_row',
    'db_record_json',
    'import_record_json',
    'field_changes_json',
    'created_at',
  ]);
  assert.match(sql, /FOREIGN KEY \(job_id\) REFERENCES soil_import_job\(job_id\)/i);
});

test('region_alias only keeps city and county disambiguation fields', () => {
  assert.deepEqual(extractColumns('region_alias'), [
    'id',
    'alias_name',
    'canonical_name',
    'region_level',
    'parent_city_name',
    'alias_source',
    'enabled',
    'created_at',
    'updated_at',
  ]);
  assert.match(sql, /UNIQUE KEY uk_region_alias_mapping/i);
  assert.match(sql, /KEY idx_region_alias_lookup/i);
});

test('snapshot and query-log tables remain after removing server chat session tables', () => {
  assert.deepEqual(extractColumns('agent_result_snapshot'), [
    'snapshot_id',
    'session_id',
    'source_turn_id',
    'source_block_id',
    'snapshot_kind',
    'query_spec_json',
    'query_spec_hash',
    'rule_version',
    'total_count',
    'expires_at',
    'created_at',
  ]);
  assert.deepEqual(extractColumns('agent_result_snapshot_item'), [
    'snapshot_id',
    'row_index',
    'payload_json',
  ]);
  assert.doesNotMatch(sql, /fk_agent_chat_session_owner/i);
  assert.doesNotMatch(sql, /fk_agent_chat_turn_session/i);
});

test('warning_template and agent_query_log retain current runtime fields plus new answer audit fields', () => {
  assert.deepEqual(extractColumns('warning_template'), [
    'template_id',
    'domain',
    'warning_type',
    'audience',
    'template_name',
    'template_text',
    'required_fields_json',
    'version',
    'enabled',
    'created_at',
    'updated_at',
  ]);
  assert.deepEqual(extractColumns('agent_query_log'), [
    'query_id',
    'session_id',
    'turn_id',
    'request_text',
    'response_text',
    'input_type',
    'intent',
    'answer_type',
    'final_status',
    'query_type',
    'query_plan_json',
    'query_spec_json',
    'sql_fingerprint',
    'executed_sql_text',
    'time_range_json',
    'filters_json',
    'group_by_json',
    'metrics_json',
    'order_by_json',
    'limit_size',
    'row_count',
    'snapshot_id',
    'executed_result_json',
    'result_digest_json',
    'source_files_json',
    'status',
    'error_message',
    'created_at',
  ]);
});
