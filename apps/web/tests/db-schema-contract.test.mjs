import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const sql = fs.readFileSync(new URL('../../../infra/mysql/init/001_init_tables.sql', import.meta.url), 'utf8');

test('mysql core tables strictly follow plans', () => {
  for (const table of [
    'fact_soil_moisture',
    'etl_import_batch',
    'soil_import_job',
    'soil_import_job_diff',
    'metric_rule',
    'admin_change_log',
    'warning_template',
    'region_alias',
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

test('region_alias table supports generated aliases and ambiguous mappings', () => {
  assert.match(sql, /CREATE TABLE IF NOT EXISTS region_alias/i);
  assert.match(sql, /alias_name\s+VARCHAR\(64\)\s+NOT NULL/i);
  assert.match(sql, /canonical_name\s+VARCHAR\(64\)\s+NOT NULL/i);
  assert.match(sql, /region_level\s+VARCHAR\(16\)\s+NOT NULL/i);
  assert.match(sql, /parent_city_name\s+VARCHAR\(64\)\s+NULL/i);
  assert.match(sql, /alias_source\s+VARCHAR\(32\)\s+NOT NULL/i);
  assert.match(sql, /UNIQUE KEY uk_region_alias_mapping/i);
  assert.match(sql, /KEY idx_region_alias_lookup/i);
});

test('fact_soil_moisture uses plan column names', () => {
  assert.match(sql, /record_id\s+VARCHAR\(64\)\s+PRIMARY KEY/i);
  assert.match(sql, /sample_time\s+DATETIME\s+NOT NULL/i);
  assert.match(sql, /create_time\s+DATETIME\s+NULL/i);
  assert.doesNotMatch(sql, /\brecord_time\b/i);
});

test('soil import job tables support preview and polling workflow', () => {
  assert.match(sql, /CREATE TABLE IF NOT EXISTS soil_import_job/i);
  assert.match(sql, /job_id\s+CHAR\(36\)\s+PRIMARY KEY/i);
  assert.match(sql, /status\s+VARCHAR\(32\)\s+NOT NULL/i);
  assert.match(sql, /processed_rows\s+INT\s+NOT NULL DEFAULT 0/i);
  assert.match(sql, /total_rows\s+INT\s+NOT NULL DEFAULT 0/i);
  assert.match(sql, /summary_json\s+JSON\s+NULL/i);

  assert.match(sql, /CREATE TABLE IF NOT EXISTS soil_import_job_diff/i);
  assert.match(sql, /diff_id\s+BIGINT\s+PRIMARY KEY AUTO_INCREMENT/i);
  assert.match(sql, /job_id\s+CHAR\(36\)\s+NOT NULL/i);
  assert.match(sql, /diff_type\s+VARCHAR\(16\)\s+NOT NULL/i);
  assert.match(sql, /db_record_json\s+JSON\s+NULL/i);
  assert.match(sql, /import_record_json\s+JSON\s+NULL/i);
  assert.match(sql, /field_changes_json\s+JSON\s+NULL/i);
  assert.match(sql, /FOREIGN KEY \(job_id\) REFERENCES soil_import_job\(job_id\)/i);
  assert.match(sql, /idx_soil_import_job_status_created_at/i);
  assert.match(sql, /idx_soil_import_job_diff_lookup/i);
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
