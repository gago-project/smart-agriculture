# `fact_soil_moisture` 表设计说明

## 表用途

`fact_soil_moisture` 是墒情域的唯一事实表。

- 原始 Excel 字段名是这张表的唯一真相，不再维护第二套内部别名。
- Agent 查询、后台列表、Excel 导入、地区别名种子都直接读取这张表。
- 运行时的异常判断、排序分值、预警状态只在内存里临时计算，不回写本表。

## 业务边界

- `time`：保留原始上游时间字段。
- `create_time`：当前查询执行统一使用的业务时间列。
- 管理字段只保留 `source_file`、`source_sheet`、`source_row`，用于追溯来源。
- 不存在批次字段、设备名称字段、乡镇字段或异常派生落库字段。

## 主键与索引

- 主键：`PRIMARY KEY (id)`
- 时间索引：`idx_soil_create_time (create_time)`
- 设备时间索引：`idx_soil_sn_create_time (sn, create_time)`
- 地区时间索引：`idx_soil_region_create_time (city, county, create_time)`

## 字段说明

| 字段 | 类型 | 可空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `varchar(64)` | 否 | 无 | 原始记录主键，直接对应 Excel 的 `id`。 |
| `sn` | `varchar(64)` | 否 | 无 | 设备序列号，Agent 与后台定位设备时统一使用。 |
| `gatewayid` | `varchar(64)` | 是 | `NULL` | 网关编号，保留上游设备接入信息。 |
| `sensorid` | `varchar(64)` | 是 | `NULL` | 传感器编号，保留原始采集侧标识。 |
| `unitid` | `varchar(64)` | 是 | `NULL` | 单元编号，适配多单元设备或上游平台原始字段。 |
| `city` | `varchar(64)` | 是 | `NULL` | 市级行政区名称。 |
| `county` | `varchar(64)` | 是 | `NULL` | 区县级行政区名称。 |
| `time` | `datetime` | 是 | `NULL` | 原始时间字段，按 Excel 原样保存，不作为当前 Agent 查询执行列。 |
| `create_time` | `datetime` | 否 | 无 | 当前查询执行统一使用的业务时间列，也是最新业务时间和排序依据。 |
| `water20cm` | `decimal(10,2)` | 是 | `NULL` | 20cm 土层含水量。 |
| `water40cm` | `decimal(10,2)` | 是 | `NULL` | 40cm 土层含水量。 |
| `water60cm` | `decimal(10,2)` | 是 | `NULL` | 60cm 土层含水量。 |
| `water80cm` | `decimal(10,2)` | 是 | `NULL` | 80cm 土层含水量。 |
| `t20cm` | `decimal(10,2)` | 是 | `NULL` | 20cm 土层温度。 |
| `t40cm` | `decimal(10,2)` | 是 | `NULL` | 40cm 土层温度。 |
| `t60cm` | `decimal(10,2)` | 是 | `NULL` | 60cm 土层温度。 |
| `t80cm` | `decimal(10,2)` | 是 | `NULL` | 80cm 土层温度。 |
| `water20cmfieldstate` | `varchar(32)` | 是 | `NULL` | 20cm 水分字段状态，保留原始质量状态。 |
| `water40cmfieldstate` | `varchar(32)` | 是 | `NULL` | 40cm 水分字段状态。 |
| `water60cmfieldstate` | `varchar(32)` | 是 | `NULL` | 60cm 水分字段状态。 |
| `water80cmfieldstate` | `varchar(32)` | 是 | `NULL` | 80cm 水分字段状态。 |
| `t20cmfieldstate` | `varchar(32)` | 是 | `NULL` | 20cm 温度字段状态。 |
| `t40cmfieldstate` | `varchar(32)` | 是 | `NULL` | 40cm 温度字段状态。 |
| `t60cmfieldstate` | `varchar(32)` | 是 | `NULL` | 60cm 温度字段状态。 |
| `t80cmfieldstate` | `varchar(32)` | 是 | `NULL` | 80cm 温度字段状态。 |
| `lat` | `decimal(10,6)` | 是 | `NULL` | 纬度。 |
| `lon` | `decimal(10,6)` | 是 | `NULL` | 经度。 |
| `source_file` | `varchar(255)` | 否 | 无 | 来源文件名，用于追溯导入来源。 |
| `source_sheet` | `varchar(128)` | 是 | `NULL` | 来源工作表名。 |
| `source_row` | `int` | 是 | `NULL` | 来源行号。 |

## 读写链路

- 写入：
  - `infra/mysql/init/003_insert_soil_data.sql`
  - `apps/web/lib/server/soilImportJobRepository.mjs`
  - `apps/web/lib/server/soilAdminRepository.mjs`
  - `apps/web/scripts/import-local-soil-excel.mjs`
- 读取：
  - `apps/agent/app/repositories/soil_repository.py`
  - `apps/web/lib/server/soilAdminRepository.mjs`
  - `apps/web/lib/server/regionAliasSeed.mjs`

## 注意事项

- 导入校验以 `id`、`sn`、`create_time` 为必填项。
- 当前所有时间过滤、排序、最新业务时间计算都必须基于 `create_time`。
- 如果需要异常说明或排序分值，应由规则引擎在运行时计算，不能把派生结果写回事实表。
