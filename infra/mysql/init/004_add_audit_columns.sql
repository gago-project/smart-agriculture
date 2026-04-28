-- P0 audit chain: add resolver and rule traceability columns to agent_query_log.
-- Safe to run multiple times (ALTER COLUMN is idempotent if column already exists;
-- MySQL 8+ supports IF NOT EXISTS for ADD COLUMN).

ALTER TABLE agent_query_log
  ADD COLUMN IF NOT EXISTS raw_args_json      JSON         NULL COMMENT 'LLM raw tool args before Resolver normalization' AFTER filters_json,
  ADD COLUMN IF NOT EXISTS resolved_args_json JSON         NULL COMMENT 'Resolver-normalized tool args sent to DB' AFTER raw_args_json,
  ADD COLUMN IF NOT EXISTS entity_confidence  VARCHAR(16)  NULL COMMENT 'high / medium / low from ParameterResolverService' AFTER resolved_args_json,
  ADD COLUMN IF NOT EXISTS time_confidence    VARCHAR(16)  NULL COMMENT 'high / medium / low from ParameterResolverService' AFTER entity_confidence,
  ADD COLUMN IF NOT EXISTS rule_version       VARCHAR(128) NULL COMMENT 'rule_code@updated_at from metric_rule table' AFTER time_confidence,
  ADD COLUMN IF NOT EXISTS empty_result_path  VARCHAR(64)  NULL COMMENT 'normalize_failed / entity_not_found / no_data_in_window' AFTER rule_version;
