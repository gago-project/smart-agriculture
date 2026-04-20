CREATE DATABASE IF NOT EXISTS smart_agriculture CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_agriculture;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(64) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'admin',
  display_name VARCHAR(128) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS etl_import_batch (
  batch_id CHAR(36) PRIMARY KEY,
  source_name VARCHAR(255) NOT NULL,
  source_path VARCHAR(512) NULL,
  imported_at DATETIME NOT NULL,
  record_count INT NOT NULL DEFAULT 0,
  status VARCHAR(32) NOT NULL DEFAULT 'completed'
);

CREATE TABLE IF NOT EXISTS soil_devices (
  device_sn VARCHAR(64) PRIMARY KEY,
  city_name VARCHAR(64) NULL,
  county_name VARCHAR(64) NULL,
  latitude DECIMAL(10,6) NULL,
  longitude DECIMAL(10,6) NULL,
  latest_record_time DATETIME NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fact_soil_moisture (
  id CHAR(36) PRIMARY KEY,
  batch_id CHAR(36) NOT NULL,
  device_sn VARCHAR(64) NOT NULL,
  gateway_id VARCHAR(64) NULL,
  sensor_id VARCHAR(64) NULL,
  unit_id VARCHAR(64) NULL,
  record_time DATETIME NOT NULL,
  water20cm DECIMAL(10,2) NULL,
  water40cm DECIMAL(10,2) NULL,
  water60cm DECIMAL(10,2) NULL,
  water80cm DECIMAL(10,2) NULL,
  t20cm DECIMAL(10,2) NULL,
  t40cm DECIMAL(10,2) NULL,
  t60cm DECIMAL(10,2) NULL,
  t80cm DECIMAL(10,2) NULL,
  latitude DECIMAL(10,6) NULL,
  longitude DECIMAL(10,6) NULL,
  city_name VARCHAR(64) NULL,
  county_name VARCHAR(64) NULL,
  created_at DATETIME NULL,
  UNIQUE KEY uk_device_time (device_sn, record_time),
  CONSTRAINT fk_fact_batch FOREIGN KEY (batch_id) REFERENCES etl_import_batch(batch_id)
);

CREATE TABLE IF NOT EXISTS metric_rule (
  rule_id VARCHAR(64) PRIMARY KEY,
  rule_name VARCHAR(128) NOT NULL,
  rule_type VARCHAR(64) NOT NULL,
  rule_definition_json JSON NOT NULL,
  enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS soil_alert_templates (
  template_id VARCHAR(64) PRIMARY KEY,
  template_name VARCHAR(128) NOT NULL,
  template_text TEXT NOT NULL,
  render_mode VARCHAR(32) NOT NULL DEFAULT 'strict',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_change_log (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  operator_name VARCHAR(128) NOT NULL,
  action_type VARCHAR(64) NOT NULL,
  target_type VARCHAR(64) NOT NULL,
  target_id VARCHAR(128) NOT NULL,
  detail_json JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
