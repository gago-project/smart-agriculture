# `fact_soil_moisture` 表设计说明

## 表作用

`fact_soil_moisture` 是当前系统的墒情事实表，保存设备上报或导入后的土壤水分、温度、地区、时间和来源追溯信息。

- Agent 查询、规则判断、地区存在性校验都以它为事实来源。
- 工作台中的墒情管理列表、编辑、删除、导入最终都落在这张表。
- `region_alias` 的静态种子也可以从这张表的地区字段去重生成。

## 主键与关联关系

- 主键：`record_id`
- 外键：`batch_id -> etl_import_batch.batch_id`
- 当前没有逻辑删除字段，删除操作是物理删除。

## 字段说明

### 记录标识与设备维度

| 字段 | 类型 | 为空 | 含义 |
| --- | --- | --- | --- |
| `record_id` | `varchar(64)` | 否 | 事实记录主键，通常对应原始 Excel 或导入数据中的唯一记录编号。 |
| `batch_id` | `char(36)` | 否 | 导入批次 ID，用于追溯该记录属于哪一次批量导入。 |
| `device_sn` | `varchar(64)` | 否 | 设备序列号，是按设备查询与最近一条查询的主键字段。 |
| `gateway_id` | `varchar(64)` | 是 | 网关编号，预留给设备网络拓扑或上游平台映射使用。 |
| `sensor_id` | `varchar(64)` | 是 | 传感器编号，适合与更细粒度的传感器体系对接。 |
| `unit_id` | `varchar(64)` | 是 | 设备单元编号，适合多单元设备场景。 |
| `device_name` | `varchar(128)` | 是 | 人类可读设备名称，主要用于后台展示和结果说明。 |

### 地区与时间维度

| 字段 | 类型 | 为空 | 含义 |
| --- | --- | --- | --- |
| `city_name` | `varchar(64)` | 是 | 市级行政区名称。 |
| `county_name` | `varchar(64)` | 是 | 区县级行政区名称。 |
| `town_name` | `varchar(64)` | 是 | 乡镇级名称。当前数据可为空。 |
| `sample_time` | `datetime` | 否 | 业务采样时间，是趋势查询、最近一条查询、时间范围过滤的核心字段。 |
| `create_time` | `datetime` | 是 | 原始记录创建时间，通常保留上游系统或文件中的原始创建时刻。 |

### 墒情与温度观测值

| 字段 | 类型 | 为空 | 含义 |
| --- | --- | --- | --- |
| `water20cm` | `decimal(10,2)` | 是 | 20cm 土层相对含水量，当前规则判断最核心的事实字段。 |
| `water40cm` | `decimal(10,2)` | 是 | 40cm 土层相对含水量。 |
| `water60cm` | `decimal(10,2)` | 是 | 60cm 土层相对含水量。 |
| `water80cm` | `decimal(10,2)` | 是 | 80cm 土层相对含水量。 |
| `t20cm` | `decimal(10,2)` | 是 | 20cm 土层温度。 |
| `t40cm` | `decimal(10,2)` | 是 | 40cm 土层温度。 |
| `t60cm` | `decimal(10,2)` | 是 | 60cm 土层温度。 |
| `t80cm` | `decimal(10,2)` | 是 | 80cm 土层温度。 |

### 字段状态与派生分析字段

| 字段 | 类型 | 为空 | 含义 |
| --- | --- | --- | --- |
| `water20cm_field_state` | `varchar(32)` | 是 | 20cm 水分字段状态，例如正常、故障、离线。 |
| `water40cm_field_state` | `varchar(32)` | 是 | 40cm 水分字段状态。 |
| `water60cm_field_state` | `varchar(32)` | 是 | 60cm 水分字段状态。 |
| `water80cm_field_state` | `varchar(32)` | 是 | 80cm 水分字段状态。 |
| `t20cm_field_state` | `varchar(32)` | 是 | 20cm 温度字段状态。 |
| `t40cm_field_state` | `varchar(32)` | 是 | 40cm 温度字段状态。 |
| `t60cm_field_state` | `varchar(32)` | 是 | 60cm 温度字段状态。 |
| `t80cm_field_state` | `varchar(32)` | 是 | 80cm 温度字段状态。 |
| `soil_anomaly_type` | `varchar(32)` | 是 | 墒情异常类型，是基于规则或导入侧计算出的派生结果，不是原始采样值本身。 |
| `soil_anomaly_score` | `decimal(10,4)` | 是 | 异常分值，常用于后台筛选或趋势判断辅助。 |

### 位置与来源追溯

| 字段 | 类型 | 为空 | 含义 |
| --- | --- | --- | --- |
| `longitude` | `decimal(10,6)` | 是 | 经度。 |
| `latitude` | `decimal(10,6)` | 是 | 纬度。 |
| `source_file` | `varchar(255)` | 否 | 来源文件名，用于回溯导入来源。 |
| `source_sheet` | `varchar(128)` | 是 | 来源工作表名。 |
| `source_row` | `int` | 是 | 来源行号，便于回溯到文件中的具体记录。 |

## 索引与约束

### 主键 / 外键

- `PRIMARY KEY (record_id)`
- `FOREIGN KEY fk_fact_batch (batch_id) REFERENCES etl_import_batch(batch_id)`

### 当前二级索引

| 索引名 | 字段 | 作用 |
| --- | --- | --- |
| `idx_soil_sample_time` | `sample_time` | 支撑按时间排序、最近业务时间、趋势类查询。 |
| `idx_soil_batch_id` | `batch_id` | 支撑按导入批次追溯、按最新批次过滤。 |
| `idx_soil_device_time` | `device_sn, sample_time` | 支撑按设备查最近一条、设备历史趋势。 |
| `idx_soil_region_time` | `city_name, county_name, town_name, sample_time` | 支撑按地区加时间范围查询。 |
| `idx_soil_anomaly` | `soil_anomaly_type, soil_anomaly_score` | 支撑异常类型或异常分值筛选。 |

## 实际读写链路

### 写入来源

- `infra/mysql/init/003_insert_soil_data.sql`：初始化全量墒情事实数据。
- `apps/web/lib/server/soilAdminRepository.mjs`：
  - `importSoilWorkbook()` 批量导入或覆盖导入；
  - `patchSoilRecord()` 后台编辑单条记录；
  - `removeSoilRecords()` 后台删除记录。
- `apps/web/scripts/import-local-soil-excel.mjs`：本地 Excel 覆盖导入脚本。

### 读取来源

- `apps/agent/app/repositories/soil_repository.py`：
  - 事实查询；
  - 最新业务时间；
  - 最新设备记录；
  - 地区是否存在、设备是否存在等校验。
- `apps/web/lib/server/soilAdminRepository.mjs`：后台列表页分页查询。
- `apps/web/scripts/generate-region-alias-seed.mjs` 与 `apps/web/lib/server/regionAliasSeed.mjs`：从地区字段生成 `region_alias` 静态种子。

## 注意事项

- `water20cm` 是当前规则判断最关键的字段，回答层不能绕开它自造事实。
- `soil_anomaly_type` / `soil_anomaly_score` 属于派生分析字段，不应替代原始采样事实。
- “最新一批”语义建议通过 `batch_id` 和 `etl_import_batch` 联动确定，而不是只看 `source_file`。
- 当前表没有 `data_status` 之类的逻辑撤回字段，因此后台删除会直接影响后续查询结果。
