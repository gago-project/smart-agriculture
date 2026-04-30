-- P0 audit chain: add resolver and rule traceability columns to agent_query_log.
-- Compatible with older MySQL variants that do not support
-- `ADD COLUMN IF NOT EXISTS` inside one ALTER TABLE statement.

USE smart_agriculture;

DELIMITER //

DROP PROCEDURE IF EXISTS ensure_column_004//

CREATE PROCEDURE ensure_column_004(
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
    SET @ensure_column_sql_004 = in_column_sql;
    PREPARE ensure_column_stmt_004 FROM @ensure_column_sql_004;
    EXECUTE ensure_column_stmt_004;
    DEALLOCATE PREPARE ensure_column_stmt_004;
  END IF;
END//

DELIMITER ;

CALL ensure_column_004(
  'agent_query_log',
  'raw_args_json',
  'ALTER TABLE agent_query_log ADD COLUMN raw_args_json JSON NULL COMMENT ''LLM raw tool args before Resolver normalization'' AFTER filters_json'
);
CALL ensure_column_004(
  'agent_query_log',
  'resolved_args_json',
  'ALTER TABLE agent_query_log ADD COLUMN resolved_args_json JSON NULL COMMENT ''Resolver-normalized tool args sent to DB'' AFTER raw_args_json'
);
CALL ensure_column_004(
  'agent_query_log',
  'entity_confidence',
  'ALTER TABLE agent_query_log ADD COLUMN entity_confidence VARCHAR(16) NULL COMMENT ''high / medium / low from ParameterResolverService'' AFTER resolved_args_json'
);
CALL ensure_column_004(
  'agent_query_log',
  'time_confidence',
  'ALTER TABLE agent_query_log ADD COLUMN time_confidence VARCHAR(16) NULL COMMENT ''high / medium / low from ParameterResolverService'' AFTER entity_confidence'
);
CALL ensure_column_004(
  'agent_query_log',
  'rule_version',
  'ALTER TABLE agent_query_log ADD COLUMN rule_version VARCHAR(128) NULL COMMENT ''rule_code@updated_at from metric_rule table'' AFTER time_confidence'
);
CALL ensure_column_004(
  'agent_query_log',
  'empty_result_path',
  'ALTER TABLE agent_query_log ADD COLUMN empty_result_path VARCHAR(64) NULL COMMENT ''normalize_failed / entity_not_found / no_data_in_window'' AFTER rule_version'
);

DROP PROCEDURE IF EXISTS ensure_column_004;
