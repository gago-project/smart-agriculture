# `etl_import_batch` 表设计说明

## 表作用

`etl_import_batch` 用于记录每一次数据导入批次的元信息，是系统理解“这批数据从哪里来、是否导入成功、共导了多少行”的入口表。

- 为 `fact_soil_moisture.batch_id` 提供外键归属。
- 支撑“最新批次”“最近一次导入”这类语义。
- 记录导入过程中的成功/失败状态和备注。

## 主键与关联关系

- 主键：`batch_id`
- 被 `fact_soil_moisture.batch_id` 引用

## 字段说明

| 字段 | 类型 | 为空 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| `batch_id` | `char(36)` | 否 | 无 | 导入批次唯一标识，一般使用 UUID。 |
| `source_name` | `varchar(64)` | 否 | 无 | 导入来源名称，例如后台上传、本地脚本导入。 |
| `source_file` | `varchar(255)` | 否 | 无 | 原始文件名或批次对应文件名。 |
| `started_at` | `datetime` | 否 | 无 | 导入开始时间。 |
| `finished_at` | `datetime` | 是 | `NULL` | 导入完成时间；失败中断或处理中可能为空。 |
| `status` | `varchar(32)` | 否 | 无 | 当前批次状态，是开放字符串字段。 |
| `raw_row_count` | `int` | 否 | `0` | 原始输入中的总行数。 |
| `loaded_row_count` | `int` | 否 | `0` | 实际写入事实表的行数。 |
| `note` | `text` | 是 | `NULL` | 补充说明或错误信息。 |

## 索引与约束

- `PRIMARY KEY (batch_id)`
- 当前 DDL 中没有额外二级索引。

## 实际读写链路

### 写入来源

- `infra/mysql/init/003_insert_soil_data.sql`：初始化全量事实数据时同步写入批次。
- `apps/web/lib/server/soilAdminRepository.mjs`：
  - 导入开始时写入一条 `status='processing'` 的批次记录；
  - 导入完成后更新为 `success`；
  - 导入失败后更新为 `failed` 并记录错误摘要。
- `apps/web/lib/server/soilImportJobRepository.mjs`：
  - 导入预览阶段只写 `soil_import_job` 与 `soil_import_job_diff`，不创建批次；
  - 管理员确认应用后才创建 `etl_import_batch`；
  - 应用成功后写入 `loaded_row_count`，应用失败后写入 `status='failed'`。

### 读取来源

- `apps/agent/app/repositories/soil_repository.py` 的 `latest_batch_id()`：按 `COALESCE(finished_at, started_at)` 倒序取最新批次。
- Agent 的时间解析和“最新一批”相关逻辑会依赖它提供的最新批次 ID。

## 当前状态值约定

当前仓库里已经实际出现或明确使用的状态值包括：

- `processing`
- `success`
- `failed`

该字段没有数据库层枚举约束，后续如需支持 `partial_success`、`cancelled` 等状态，需要在应用层统一约定。

## 注意事项

- 一条批次记录并不保证事实表一定已经全部写入成功，必须结合 `status` 与 `loaded_row_count` 一起理解。
- “覆盖导入”通常会先创建新批次，再清空或重写事实表内容，因此批次日志与事实内容应联动排查。
- 当前没有单独的批次审计表；导入级异常说明主要靠 `status` 与 `note` 保留。
