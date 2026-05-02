CREATE DATABASE IF NOT EXISTS smart_agriculture CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_agriculture;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS agent_result_snapshot_item;
DROP TABLE IF EXISTS agent_result_snapshot;
DROP TABLE IF EXISTS agent_chat_turn;
DROP TABLE IF EXISTS agent_chat_session;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE IF NOT EXISTS soil_import_job (
  job_id CHAR(36) PRIMARY KEY,
  filename VARCHAR(255) NOT NULL,
  requested_by_user_id BIGINT NULL,
  requested_by_username VARCHAR(64) NULL,
  status VARCHAR(32) NOT NULL,
  apply_mode VARCHAR(16) NULL,
  processed_rows INT NOT NULL DEFAULT 0,
  total_rows INT NOT NULL DEFAULT 0,
  summary_json JSON NULL,
  error_message TEXT NULL,
  finished_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS soil_import_job_diff (
  diff_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  job_id CHAR(36) NOT NULL,
  diff_type VARCHAR(16) NOT NULL,
  id VARCHAR(64) NULL,
  source_row INT NULL,
  db_record_json JSON NULL,
  import_record_json JSON NULL,
  field_changes_json JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_soil_import_job_diff_job FOREIGN KEY (job_id) REFERENCES soil_import_job(job_id)
);

CREATE TABLE IF NOT EXISTS fact_soil_moisture (
  id VARCHAR(64) PRIMARY KEY,
  sn VARCHAR(64) NOT NULL,
  gatewayid VARCHAR(64) NULL,
  sensorid VARCHAR(64) NULL,
  unitid VARCHAR(64) NULL,
  city VARCHAR(64) NULL,
  county VARCHAR(64) NULL,
  time DATETIME NULL,
  create_time DATETIME NOT NULL,
  water20cm DECIMAL(10,2) NULL,
  water40cm DECIMAL(10,2) NULL,
  water60cm DECIMAL(10,2) NULL,
  water80cm DECIMAL(10,2) NULL,
  t20cm DECIMAL(10,2) NULL,
  t40cm DECIMAL(10,2) NULL,
  t60cm DECIMAL(10,2) NULL,
  t80cm DECIMAL(10,2) NULL,
  water20cmfieldstate VARCHAR(32) NULL,
  water40cmfieldstate VARCHAR(32) NULL,
  water60cmfieldstate VARCHAR(32) NULL,
  water80cmfieldstate VARCHAR(32) NULL,
  t20cmfieldstate VARCHAR(32) NULL,
  t40cmfieldstate VARCHAR(32) NULL,
  t60cmfieldstate VARCHAR(32) NULL,
  t80cmfieldstate VARCHAR(32) NULL,
  lat DECIMAL(10,6) NULL,
  lon DECIMAL(10,6) NULL
);

CREATE TABLE IF NOT EXISTS metric_rule (
  rule_code VARCHAR(64) PRIMARY KEY,
  rule_name VARCHAR(128) NOT NULL,
  rule_scope VARCHAR(64) NOT NULL,
  rule_definition_json JSON NOT NULL,
  enabled TINYINT NOT NULL DEFAULT 1,
  updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS admin_change_log (
  id BIGINT PRIMARY KEY,
  operator_user_id BIGINT NULL,
  operator_username VARCHAR(64) NULL,
  operation VARCHAR(64) NOT NULL,
  target_table VARCHAR(128) NOT NULL,
  target_id VARCHAR(128) NULL,
  before_json JSON NULL,
  after_json JSON NULL,
  created_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS warning_template (
  template_id VARCHAR(64) PRIMARY KEY,
  domain VARCHAR(32) NOT NULL,
  warning_type VARCHAR(64) NOT NULL,
  audience VARCHAR(64) NOT NULL,
  template_name VARCHAR(128) NOT NULL,
  template_text TEXT NOT NULL,
  required_fields_json JSON NOT NULL,
  version VARCHAR(64) NOT NULL,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS region_alias (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  alias_name VARCHAR(64) NOT NULL,
  canonical_name VARCHAR(64) NOT NULL,
  region_level VARCHAR(16) NOT NULL,
  parent_city_name VARCHAR(64) NULL,
  alias_source VARCHAR(32) NOT NULL,
  enabled TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_region_alias_mapping (alias_name, canonical_name, region_level, enabled),
  KEY idx_region_alias_lookup (enabled, alias_name, region_level)
);

CREATE TABLE IF NOT EXISTS auth_user (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  password_salt VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'user',
  is_active TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_auth_username (username)
);

CREATE TABLE IF NOT EXISTS auth_session (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  token_hash VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL,
  expires_at DATETIME NOT NULL,
  last_used_at DATETIME NOT NULL,
  UNIQUE KEY uk_auth_token_hash (token_hash),
  KEY idx_auth_session_user (user_id),
  KEY idx_auth_session_expires_at (expires_at),
  CONSTRAINT fk_auth_session_user FOREIGN KEY (user_id) REFERENCES auth_user(id)
);

CREATE TABLE IF NOT EXISTS agent_result_snapshot (
  snapshot_id VARCHAR(64) PRIMARY KEY,
  session_id CHAR(36) NOT NULL,
  source_turn_id INT NOT NULL,
  source_block_id VARCHAR(128) NOT NULL,
  snapshot_kind VARCHAR(32) NOT NULL,
  query_spec_json JSON NOT NULL,
  query_spec_hash VARCHAR(64) NOT NULL,
  rule_version VARCHAR(64) NULL,
  total_count INT NOT NULL DEFAULT 0,
  expires_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_result_snapshot_item (
  snapshot_id VARCHAR(64) NOT NULL,
  row_index INT NOT NULL,
  payload_json JSON NOT NULL,
  PRIMARY KEY (snapshot_id, row_index),
  CONSTRAINT fk_agent_result_snapshot_item_snapshot FOREIGN KEY (snapshot_id) REFERENCES agent_result_snapshot(snapshot_id)
);

CREATE TABLE IF NOT EXISTS agent_query_log (
  query_id VARCHAR(64) PRIMARY KEY,
  session_id VARCHAR(64) NOT NULL,
  turn_id INT NOT NULL,
  request_text TEXT NULL,
  response_text TEXT NULL,
  input_type VARCHAR(32) NULL,
  intent VARCHAR(64) NULL,
  answer_type VARCHAR(64) NULL,
  final_status VARCHAR(64) NULL,
  query_type VARCHAR(64) NOT NULL,
  query_plan_json JSON NOT NULL,
  query_spec_json JSON NULL,
  sql_fingerprint VARCHAR(255) NULL,
  executed_sql_text TEXT NULL,
  time_range_json JSON NOT NULL,
  filters_json JSON NOT NULL,
  group_by_json JSON NULL,
  metrics_json JSON NULL,
  order_by_json JSON NULL,
  limit_size INT NULL,
  row_count INT NOT NULL,
  snapshot_id VARCHAR(64) NULL,
  executed_result_json JSON NULL,
  result_digest_json JSON NULL,
  source_files_json JSON NULL,
  status VARCHAR(32) NOT NULL,
  error_message TEXT NULL,
  created_at DATETIME NOT NULL
);

DELIMITER //

DROP PROCEDURE IF EXISTS ensure_index//

CREATE PROCEDURE ensure_index(
  IN in_table_name VARCHAR(64),
  IN in_index_name VARCHAR(64),
  IN in_index_sql TEXT
)
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = in_table_name
      AND index_name = in_index_name
  ) THEN
    SET @ensure_index_sql = in_index_sql;
    PREPARE ensure_stmt FROM @ensure_index_sql;
    EXECUTE ensure_stmt;
    DEALLOCATE PREPARE ensure_stmt;
  END IF;
END//

DROP PROCEDURE IF EXISTS ensure_column//

CREATE PROCEDURE ensure_column(
  IN in_table_name VARCHAR(64),
  IN in_column_name VARCHAR(64),
  IN in_column_sql TEXT
)
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = in_table_name
      AND column_name = in_column_name
  ) THEN
    SET @ensure_column_sql = in_column_sql;
    PREPARE ensure_column_stmt FROM @ensure_column_sql;
    EXECUTE ensure_column_stmt;
    DEALLOCATE PREPARE ensure_column_stmt;
  END IF;
END//

DROP PROCEDURE IF EXISTS drop_column_if_exists//

CREATE PROCEDURE drop_column_if_exists(
  IN in_table_name VARCHAR(64),
  IN in_column_name VARCHAR(64),
  IN in_column_sql TEXT
)
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = in_table_name
      AND column_name = in_column_name
  ) THEN
    SET @drop_column_sql = in_column_sql;
    PREPARE drop_column_stmt FROM @drop_column_sql;
    EXECUTE drop_column_stmt;
    DEALLOCATE PREPARE drop_column_stmt;
  END IF;
END//

DROP PROCEDURE IF EXISTS drop_index_if_exists//

CREATE PROCEDURE drop_index_if_exists(
  IN in_table_name VARCHAR(64),
  IN in_index_name VARCHAR(64),
  IN in_index_sql TEXT
)
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = in_table_name
      AND index_name = in_index_name
  ) THEN
    SET @drop_index_sql = in_index_sql;
    PREPARE drop_index_stmt FROM @drop_index_sql;
    EXECUTE drop_index_stmt;
    DEALLOCATE PREPARE drop_index_stmt;
  END IF;
END//

DELIMITER ;

CALL drop_column_if_exists('fact_soil_moisture', 'source_file', 'ALTER TABLE fact_soil_moisture DROP COLUMN source_file');
CALL drop_column_if_exists('fact_soil_moisture', 'source_sheet', 'ALTER TABLE fact_soil_moisture DROP COLUMN source_sheet');
CALL drop_column_if_exists('fact_soil_moisture', 'source_row', 'ALTER TABLE fact_soil_moisture DROP COLUMN source_row');
CALL drop_index_if_exists('agent_result_snapshot_item', 'idx_agent_result_snapshot_item_lookup', 'ALTER TABLE agent_result_snapshot_item DROP INDEX idx_agent_result_snapshot_item_lookup');
CALL drop_column_if_exists('agent_result_snapshot_item', 'entity_key', 'ALTER TABLE agent_result_snapshot_item DROP COLUMN entity_key');
CALL drop_column_if_exists('agent_result_snapshot_item', 'city', 'ALTER TABLE agent_result_snapshot_item DROP COLUMN city');
CALL drop_column_if_exists('agent_result_snapshot_item', 'county', 'ALTER TABLE agent_result_snapshot_item DROP COLUMN county');
CALL drop_column_if_exists('agent_result_snapshot_item', 'sn', 'ALTER TABLE agent_result_snapshot_item DROP COLUMN sn');
CALL drop_column_if_exists('agent_result_snapshot_item', 'latest_create_time', 'ALTER TABLE agent_result_snapshot_item DROP COLUMN latest_create_time');
CALL ensure_column('agent_query_log', 'request_text', 'ALTER TABLE agent_query_log ADD COLUMN request_text TEXT NULL AFTER turn_id');
CALL ensure_column('agent_query_log', 'response_text', 'ALTER TABLE agent_query_log ADD COLUMN response_text TEXT NULL AFTER request_text');
CALL ensure_column('agent_query_log', 'input_type', 'ALTER TABLE agent_query_log ADD COLUMN input_type VARCHAR(32) NULL AFTER response_text');
CALL ensure_column('agent_query_log', 'intent', 'ALTER TABLE agent_query_log ADD COLUMN intent VARCHAR(64) NULL AFTER input_type');
CALL ensure_column('agent_query_log', 'answer_type', 'ALTER TABLE agent_query_log ADD COLUMN answer_type VARCHAR(64) NULL AFTER intent');
CALL ensure_column('agent_query_log', 'final_status', 'ALTER TABLE agent_query_log ADD COLUMN final_status VARCHAR(64) NULL AFTER answer_type');
CALL ensure_column('agent_query_log', 'query_spec_json', 'ALTER TABLE agent_query_log ADD COLUMN query_spec_json JSON NULL AFTER query_plan_json');
CALL ensure_column('agent_query_log', 'executed_sql_text', 'ALTER TABLE agent_query_log ADD COLUMN executed_sql_text TEXT NULL AFTER sql_fingerprint');
CALL ensure_column('agent_query_log', 'snapshot_id', 'ALTER TABLE agent_query_log ADD COLUMN snapshot_id VARCHAR(64) NULL AFTER row_count');
CALL ensure_column('agent_query_log', 'executed_result_json', 'ALTER TABLE agent_query_log ADD COLUMN executed_result_json JSON NULL AFTER row_count');
CALL ensure_column('agent_query_log', 'result_digest_json', 'ALTER TABLE agent_query_log ADD COLUMN result_digest_json JSON NULL AFTER executed_result_json');
CALL drop_column_if_exists('agent_query_log', 'result_preview_json', 'ALTER TABLE agent_query_log DROP COLUMN result_preview_json');

CALL ensure_index('fact_soil_moisture', 'idx_soil_create_time', 'CREATE INDEX idx_soil_create_time ON fact_soil_moisture (create_time)');
CALL ensure_index('fact_soil_moisture', 'idx_soil_sn_create_time', 'CREATE INDEX idx_soil_sn_create_time ON fact_soil_moisture (sn, create_time)');
CALL ensure_index('fact_soil_moisture', 'idx_soil_region_create_time', 'CREATE INDEX idx_soil_region_create_time ON fact_soil_moisture (city, county, create_time)');
CALL ensure_index('soil_import_job', 'idx_soil_import_job_status_created_at', 'CREATE INDEX idx_soil_import_job_status_created_at ON soil_import_job (status, created_at)');
CALL ensure_index('soil_import_job_diff', 'idx_soil_import_job_diff_lookup', 'CREATE INDEX idx_soil_import_job_diff_lookup ON soil_import_job_diff (job_id, diff_type, diff_id)');
CALL ensure_index('metric_rule', 'idx_metric_rule_scope_enabled', 'CREATE INDEX idx_metric_rule_scope_enabled ON metric_rule (enabled, rule_scope, updated_at)');
CALL ensure_index('agent_result_snapshot', 'idx_agent_result_snapshot_session_turn', 'CREATE INDEX idx_agent_result_snapshot_session_turn ON agent_result_snapshot (session_id, source_turn_id)');
CALL ensure_index('agent_result_snapshot', 'idx_agent_result_snapshot_expires_at', 'CREATE INDEX idx_agent_result_snapshot_expires_at ON agent_result_snapshot (expires_at)');
CALL ensure_index('agent_query_log', 'idx_aql_session_turn', 'CREATE INDEX idx_aql_session_turn ON agent_query_log (session_id, turn_id)');
CALL ensure_index('agent_query_log', 'idx_aql_created_at', 'CREATE INDEX idx_aql_created_at ON agent_query_log (created_at)');
CALL ensure_index('agent_query_log', 'idx_aql_query_type_created_at', 'CREATE INDEX idx_aql_query_type_created_at ON agent_query_log (query_type, created_at)');
CALL ensure_index('agent_query_log', 'idx_aql_status_created_at', 'CREATE INDEX idx_aql_status_created_at ON agent_query_log (status, created_at)');

DROP PROCEDURE IF EXISTS ensure_index;
DROP PROCEDURE IF EXISTS ensure_column;
DROP PROCEDURE IF EXISTS drop_column_if_exists;
DROP PROCEDURE IF EXISTS drop_index_if_exists;
