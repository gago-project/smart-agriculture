CREATE DATABASE IF NOT EXISTS smart_agriculture CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_agriculture;

CREATE TABLE IF NOT EXISTS etl_import_batch (
  batch_id CHAR(36) PRIMARY KEY,
  source_name VARCHAR(64) NOT NULL,
  source_file VARCHAR(255) NOT NULL,
  started_at DATETIME NOT NULL,
  finished_at DATETIME NULL,
  status VARCHAR(32) NOT NULL,
  raw_row_count INT NOT NULL DEFAULT 0,
  loaded_row_count INT NOT NULL DEFAULT 0,
  note TEXT NULL
);

CREATE TABLE IF NOT EXISTS fact_soil_moisture (
  record_id VARCHAR(64) PRIMARY KEY,
  batch_id CHAR(36) NOT NULL,
  device_sn VARCHAR(64) NOT NULL,
  gateway_id VARCHAR(64) NULL,
  sensor_id VARCHAR(64) NULL,
  unit_id VARCHAR(64) NULL,
  device_name VARCHAR(128) NULL,
  city_name VARCHAR(64) NULL,
  county_name VARCHAR(64) NULL,
  town_name VARCHAR(64) NULL,
  sample_time DATETIME NOT NULL,
  create_time DATETIME NULL,
  water20cm DECIMAL(10,2) NULL,
  water40cm DECIMAL(10,2) NULL,
  water60cm DECIMAL(10,2) NULL,
  water80cm DECIMAL(10,2) NULL,
  t20cm DECIMAL(10,2) NULL,
  t40cm DECIMAL(10,2) NULL,
  t60cm DECIMAL(10,2) NULL,
  t80cm DECIMAL(10,2) NULL,
  water20cm_field_state VARCHAR(32) NULL,
  water40cm_field_state VARCHAR(32) NULL,
  water60cm_field_state VARCHAR(32) NULL,
  water80cm_field_state VARCHAR(32) NULL,
  t20cm_field_state VARCHAR(32) NULL,
  t40cm_field_state VARCHAR(32) NULL,
  t60cm_field_state VARCHAR(32) NULL,
  t80cm_field_state VARCHAR(32) NULL,
  soil_anomaly_type VARCHAR(32) NULL,
  soil_anomaly_score DECIMAL(10,4) NULL,
  longitude DECIMAL(10,6) NULL,
  latitude DECIMAL(10,6) NULL,
  source_file VARCHAR(255) NOT NULL,
  source_sheet VARCHAR(128) NULL,
  source_row INT NULL,
  CONSTRAINT fk_fact_batch FOREIGN KEY (batch_id) REFERENCES etl_import_batch(batch_id)
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
  sql_fingerprint VARCHAR(255) NULL,
  executed_sql_text TEXT NULL,
  time_range_json JSON NOT NULL,
  filters_json JSON NOT NULL,
  group_by_json JSON NULL,
  metrics_json JSON NULL,
  order_by_json JSON NULL,
  limit_size INT NULL,
  row_count INT NOT NULL,
  executed_result_json JSON NULL,
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

DELIMITER ;

CALL ensure_column('agent_query_log', 'request_text', 'ALTER TABLE agent_query_log ADD COLUMN request_text TEXT NULL AFTER turn_id');
CALL ensure_column('agent_query_log', 'response_text', 'ALTER TABLE agent_query_log ADD COLUMN response_text TEXT NULL AFTER request_text');
CALL ensure_column('agent_query_log', 'input_type', 'ALTER TABLE agent_query_log ADD COLUMN input_type VARCHAR(32) NULL AFTER response_text');
CALL ensure_column('agent_query_log', 'intent', 'ALTER TABLE agent_query_log ADD COLUMN intent VARCHAR(64) NULL AFTER input_type');
CALL ensure_column('agent_query_log', 'answer_type', 'ALTER TABLE agent_query_log ADD COLUMN answer_type VARCHAR(64) NULL AFTER intent');
CALL ensure_column('agent_query_log', 'final_status', 'ALTER TABLE agent_query_log ADD COLUMN final_status VARCHAR(64) NULL AFTER answer_type');
CALL ensure_column('agent_query_log', 'executed_sql_text', 'ALTER TABLE agent_query_log ADD COLUMN executed_sql_text TEXT NULL AFTER sql_fingerprint');
CALL ensure_column('agent_query_log', 'executed_result_json', 'ALTER TABLE agent_query_log ADD COLUMN executed_result_json JSON NULL AFTER row_count');

CALL ensure_index('fact_soil_moisture', 'idx_soil_sample_time', 'CREATE INDEX idx_soil_sample_time ON fact_soil_moisture (sample_time)');
CALL ensure_index('fact_soil_moisture', 'idx_soil_batch_id', 'CREATE INDEX idx_soil_batch_id ON fact_soil_moisture (batch_id)');
CALL ensure_index('fact_soil_moisture', 'idx_soil_device_time', 'CREATE INDEX idx_soil_device_time ON fact_soil_moisture (device_sn, sample_time)');
CALL ensure_index('fact_soil_moisture', 'idx_soil_region_time', 'CREATE INDEX idx_soil_region_time ON fact_soil_moisture (city_name, county_name, town_name, sample_time)');
CALL ensure_index('fact_soil_moisture', 'idx_soil_anomaly', 'CREATE INDEX idx_soil_anomaly ON fact_soil_moisture (soil_anomaly_type, soil_anomaly_score)');
CALL ensure_index('metric_rule', 'idx_metric_rule_scope_enabled', 'CREATE INDEX idx_metric_rule_scope_enabled ON metric_rule (enabled, rule_scope, updated_at)');
CALL ensure_index('agent_query_log', 'idx_aql_session_turn', 'CREATE INDEX idx_aql_session_turn ON agent_query_log (session_id, turn_id)');
CALL ensure_index('agent_query_log', 'idx_aql_created_at', 'CREATE INDEX idx_aql_created_at ON agent_query_log (created_at)');
CALL ensure_index('agent_query_log', 'idx_aql_query_type_created_at', 'CREATE INDEX idx_aql_query_type_created_at ON agent_query_log (query_type, created_at)');
CALL ensure_index('agent_query_log', 'idx_aql_status_created_at', 'CREATE INDEX idx_aql_status_created_at ON agent_query_log (status, created_at)');

DROP PROCEDURE IF EXISTS ensure_index;
DROP PROCEDURE IF EXISTS ensure_column;
