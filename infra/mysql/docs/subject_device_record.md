# `subject_device_record` 表设计说明

## 表用途

`subject_device_record` 是苏农云平台接入设备的**台账表**，存储平台注册的所有传感/监测设备。

- 原始 Excel 字段名是这张表的唯一真相，不维护第二套内部别名。
- Agent 的「接入设备总数」查询从此表统计（`WHERE type = '土壤墒情仪'`），不依赖 `fact_soil_moisture`。
- 与 `fact_soil_moisture` 的关联键为 `sn`（设备序列号）。

## 业务边界

- 此表记录**设备台账**，不记录采集数据。设备数量是静态计数，不受时间窗过滤影响。
- `type` 字段区分设备类型：`土壤墒情仪` / `智能性诱监测设备` / `监控摄像头` / `流行性病害监测仪` 等。
- Agent 当前只查询 `type = '土壤墒情仪'` 的行数。

## 与 `fact_soil_moisture` 的关系

| 维度 | `subject_device_record` | `fact_soil_moisture` |
|------|------------------------|----------------------|
| 用途 | 设备台账（静态） | 采集事实数据（时序） |
| 粒度 | 每设备一行 | 每次采集一行 |
| 关联键 | `sn` | `sn` |
| Agent 查询场景 | 接入总数、设备列表 | 墒情数据、预警分析 |

## 主键与索引

- 主键：`PRIMARY KEY (id)`
- 设备序列号：`INDEX idx_subject_device_record_sn (sn)`
- 设备类型：`INDEX idx_subject_device_record_type (type)`
- 地区：`INDEX idx_subject_device_record_city (city, county)`

## 字段说明

| 字段 | 类型 | 可空 | 说明 |
| --- | --- | --- | --- |
| `id` | `VARCHAR(36)` | 否 | UUID 主键，直接对应 Excel 的 `id`。 |
| `device_name` | `VARCHAR(255)` | 是 | 设备名称。 |
| `region_code` | `VARCHAR(64)` | 是 | 行政区划代码。 |
| `region_name` | `VARCHAR(128)` | 是 | 行政区划名称（可能与 city/county 有冗余）。 |
| `lat` | `VARCHAR(32)` | 是 | 纬度（保留原始字符串精度）。 |
| `lon` | `VARCHAR(32)` | 是 | 经度（保留原始字符串精度）。 |
| `sn` | `VARCHAR(64)` | 是 | 设备序列号，与 `fact_soil_moisture.sn` 关联。 |
| `type` | `VARCHAR(64)` | 是 | 设备类型。当前 Agent 只使用 `土壤墒情仪`。 |
| `create_time` | `DATETIME` | 是 | 设备台账创建时间（非采集时间）。 |
| `p_id` | `VARCHAR(64)` | 是 | 上级设备/节点 ID。 |
| `brand` | `VARCHAR(128)` | 是 | 设备品牌。 |
| `device_model` | `VARCHAR(128)` | 是 | 设备型号。 |
| `agreement` | `VARCHAR(64)` | 是 | 通信协议类型。 |
| `legal_person` | `VARCHAR(64)` | 是 | 法人/负责人。 |
| `contact_information` | `VARCHAR(128)` | 是 | 联系方式。 |
| `address` | `VARCHAR(255)` | 是 | 安装地址。 |
| `insect_type` | `VARCHAR(128)` | 是 | 病虫害类型（虫情监测设备专用字段）。 |
| `city` | `VARCHAR(64)` | 是 | 市级行政区。 |
| `county` | `VARCHAR(64)` | 是 | 区县级行政区。 |
| `tag` | `VARCHAR(255)` | 是 | 标签/备注。 |

## 数据分布（示例）

Excel 原始导入后，按 `type` 统计：

| 设备类型 | 数量 |
|----------|-----:|
| 智能性诱监测设备 | 1098 |
| **土壤墒情仪** | **528** |
| 监控摄像头 | 183 |
| 流行性病害监测仪 | 49 |

## 读写链路

- 写入：
  - `infra/mysql/init/005_add_subject_device_record.sql`（建表）
  - `apps/web/scripts/import-device-ledger.mjs`（Excel 导入）
- 读取：
  - `apps/agent/app/repositories/soil_repository.py`（`total_soil_device_count[_async]()`）

## 导入说明

将设备台账 Excel 放到 `infra/mysql/local/device_ledger.local.xlsx`（或设置 `DEVICE_LEDGER_EXCEL_SOURCE`），然后执行：

```bash
node apps/web/scripts/import-device-ledger.mjs
```

脚本幂等，可重复执行（`ON DUPLICATE KEY UPDATE`）。

## 注意事项

- `id` 为 UUID，必填，是幂等导入的唯一键。
- 此表不做时间窗过滤，Agent 查询直接 COUNT 全表（按 `type` 过滤）。
- `sn` 允许为 NULL（非墒情仪设备可能没有 SNS 编号），与 `fact_soil_moisture` 关联时需注意。
- 如需按城市统计设备数，查 `city` 字段即可，但 Agent 当前只支持全省总数。
