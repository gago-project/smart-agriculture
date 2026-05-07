-- warning_disposal_record: 预警处置记录表
-- 数据来源：1111.xlsx，仅导入 warn_type='墒情预警' 的行
CREATE TABLE IF NOT EXISTS warning_disposal_record (
  id                     VARCHAR(36)   NOT NULL   COMMENT '原始系统 UUID',
  sn                     VARCHAR(32)   NOT NULL   COMMENT '设备编号，关联 fact_soil_moisture.sn',
  warn_time              DATETIME      NOT NULL   COMMENT '预警触发时间',
  create_time            DATETIME          NULL   COMMENT '记录创建时间',
  pub_time               DATETIME          NULL   COMMENT '处置建议发布时间，NULL 表示尚未发布',
  pub_status             TINYINT       NOT NULL   COMMENT '1待处理 2超时未处理 3已处理 4超时处理',
  warn_level             VARCHAR(16)   NOT NULL   COMMENT '涝渍 / 重旱',
  warn_level_code        TINYINT           NULL   COMMENT '1涝渍 2重旱',
  warn_value             VARCHAR(16)       NULL   COMMENT '预警时含水量值（百分比字符串）',
  city                   VARCHAR(32)       NULL   COMMENT '设备所在市，从 address 解析或 sys_region JOIN',
  county                 VARCHAR(32)       NULL   COMMENT '设备所在区县',
  region_code            VARCHAR(12)       NULL   COMMENT '乡镇级行政区划编码',
  address                VARCHAR(64)       NULL   COMMENT '原始地址字段，如「苏州市昆山市」',
  do_advice              TEXT              NULL   COMMENT '处置建议内容',
  pub_user               VARCHAR(64)       NULL   COMMENT '发布人 ID',
  pub_user_name          VARCHAR(128)      NULL   COMMENT '发布人姓名或联系方式',
  pub_short_message_flag TINYINT           NULL   COMMENT '0不发短信 1发短信',
  content                TEXT              NULL   COMMENT '预警原始内容文本',
  PRIMARY KEY (id),
  INDEX idx_sn               (sn),
  INDEX idx_warn_time        (warn_time),
  INDEX idx_city_warn_time   (city, warn_time),
  INDEX idx_county_warn_time (county, warn_time),
  INDEX idx_pub_status       (pub_status),
  INDEX idx_region_code      (region_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='墒情预警处置记录表';
