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

CREATE INDEX IF NOT EXISTS idx_subject_device_record_sn   ON subject_device_record (sn);
CREATE INDEX IF NOT EXISTS idx_subject_device_record_type ON subject_device_record (type);
CREATE INDEX IF NOT EXISTS idx_subject_device_record_city ON subject_device_record (city, county);
