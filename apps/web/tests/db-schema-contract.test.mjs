import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const sql = fs.readFileSync(new URL('../../../infra/mysql/init/001_init_tables.sql', import.meta.url), 'utf8');

test('mysql core tables strictly follow plans', () => {
  for (const table of [
    'fact_soil_moisture',
    'etl_import_batch',
    'metric_rule',
    'admin_change_log',
    'warning_template',
    'agent_query_log',
    'auth_user',
    'auth_session',
  ]) {
    assert.match(sql, new RegExp(`CREATE TABLE IF NOT EXISTS ${table}\\b`));
  }

  for (const forbidden of ['users', 'soil_devices', 'soil_alert_templates']) {
    assert.doesNotMatch(sql, new RegExp(`CREATE TABLE IF NOT EXISTS ${forbidden}\\b`));
  }
});

test('fact_soil_moisture uses plan column names', () => {
  assert.match(sql, /record_id\s+VARCHAR\(64\)\s+PRIMARY KEY/i);
  assert.match(sql, /sample_time\s+DATETIME\s+NOT NULL/i);
  assert.match(sql, /create_time\s+DATETIME\s+NULL/i);
  assert.doesNotMatch(sql, /\brecord_time\b/i);
});

test('warning_template and agent_query_log columns follow plans', () => {
  assert.match(sql, /CREATE TABLE IF NOT EXISTS warning_template/i);
  assert.match(sql, /required_fields_json\s+JSON\s+NOT NULL/i);
  assert.match(sql, /version\s+VARCHAR\(64\)\s+NOT NULL/i);
  assert.match(sql, /CREATE TABLE IF NOT EXISTS agent_query_log/i);
  assert.match(sql, /query_id\s+VARCHAR\(64\)\s+PRIMARY KEY/i);
  assert.match(sql, /query_plan_json\s+JSON\s+NOT NULL/i);
  assert.match(sql, /request_text\s+TEXT\s+NULL/i);
  assert.match(sql, /response_text\s+TEXT\s+NULL/i);
  assert.match(sql, /input_type\s+VARCHAR\(32\)\s+NULL/i);
  assert.match(sql, /intent\s+VARCHAR\(64\)\s+NULL/i);
  assert.match(sql, /answer_type\s+VARCHAR\(64\)\s+NULL/i);
  assert.match(sql, /final_status\s+VARCHAR\(64\)\s+NULL/i);
  assert.match(sql, /executed_sql_text\s+TEXT\s+NULL/i);
  assert.match(sql, /executed_result_json\s+JSON\s+NULL/i);
  assert.doesNotMatch(sql, /result_preview_json\s+JSON\s+NULL/i);
});

test('mysql init drops deprecated query log preview column on existing databases', () => {
  assert.match(sql, /DROP PROCEDURE IF EXISTS drop_column_if_exists\/\//i);
  assert.match(sql, /CREATE PROCEDURE drop_column_if_exists\(/i);
  assert.match(sql, /CALL drop_column_if_exists\('agent_query_log', 'result_preview_json'/i);
});

test('auth tables use database-backed user and session design', () => {
  assert.match(sql, /CREATE TABLE IF NOT EXISTS auth_user/i);
  assert.match(sql, /username\s+VARCHAR\(64\)\s+NOT NULL/i);
  assert.match(sql, /password_hash\s+VARCHAR\(255\)\s+NOT NULL/i);
  assert.match(sql, /password_salt\s+VARCHAR\(255\)\s+NOT NULL/i);
  assert.match(sql, /role\s+VARCHAR\(32\)\s+NOT NULL DEFAULT 'user'/i);
  assert.match(sql, /CREATE TABLE IF NOT EXISTS auth_session/i);
  assert.match(sql, /token_hash\s+VARCHAR\(255\)\s+NOT NULL/i);
  assert.match(sql, /FOREIGN KEY \(user_id\) REFERENCES auth_user\(id\)/i);
});
