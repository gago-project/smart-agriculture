-- sys_region: 行政区划表，精确到乡镇（9位编码）
-- 数据来源：sys_region.xls
CREATE TABLE IF NOT EXISTS sys_region (
  id           VARCHAR(36)  NOT NULL,
  region_code  VARCHAR(12)  NOT NULL  COMMENT '行政区划编码，6位=省/市/县，9位=乡镇',
  region_name  VARCHAR(64)  NOT NULL  COMMENT '区划名称',
  parent_code  VARCHAR(12)      NULL  COMMENT '上级区划编码',
  region_level TINYINT      NOT NULL  COMMENT '1省 2市 3县/区 4乡镇/街道',
  lon          VARCHAR(24)      NULL  COMMENT '经度',
  lat          VARCHAR(24)      NULL  COMMENT '纬度',
  created_at   DATETIME         NULL,
  updated_at   DATETIME         NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_region_code (region_code),
  INDEX idx_parent_code (parent_code),
  INDEX idx_region_level (region_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行政区划表';
