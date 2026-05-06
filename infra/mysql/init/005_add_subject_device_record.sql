USE smart_agriculture;

CREATE TABLE IF NOT EXISTS subject_device_record (
  id             VARCHAR(36)   NOT NULL PRIMARY KEY,
  device_name    VARCHAR(255)  NULL,
  region_code    VARCHAR(64)   NULL,
  region_name    VARCHAR(128)  NULL,
  lat            VARCHAR(32)   NULL,
  lon            VARCHAR(32)   NULL,
  sn             VARCHAR(64)   NULL,
  type           VARCHAR(64)   NULL,
  create_time    DATETIME      NULL,
  p_id           VARCHAR(64)   NULL,
  brand          VARCHAR(128)  NULL,
  device_model   VARCHAR(128)  NULL,
  agreement      VARCHAR(64)   NULL,
  legal_person   VARCHAR(64)   NULL,
  contact_information VARCHAR(128) NULL,
  address        VARCHAR(255)  NULL,
  insect_type    VARCHAR(128)  NULL,
  city           VARCHAR(64)   NULL,
  county         VARCHAR(64)   NULL,
  tag            VARCHAR(255)  NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELIMITER //

DROP PROCEDURE IF EXISTS ensure_index_005//

CREATE PROCEDURE ensure_index_005(
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
    SET @ensure_index_sql_005 = in_index_sql;
    PREPARE ensure_index_stmt_005 FROM @ensure_index_sql_005;
    EXECUTE ensure_index_stmt_005;
    DEALLOCATE PREPARE ensure_index_stmt_005;
  END IF;
END//

DELIMITER ;

CALL ensure_index_005(
  'subject_device_record',
  'idx_subject_device_record_sn',
  'CREATE INDEX idx_subject_device_record_sn ON subject_device_record (sn)'
);
CALL ensure_index_005(
  'subject_device_record',
  'idx_subject_device_record_type',
  'CREATE INDEX idx_subject_device_record_type ON subject_device_record (type)'
);
CALL ensure_index_005(
  'subject_device_record',
  'idx_subject_device_record_city',
  'CREATE INDEX idx_subject_device_record_city ON subject_device_record (city, county)'
);

DROP PROCEDURE IF EXISTS ensure_index_005;
