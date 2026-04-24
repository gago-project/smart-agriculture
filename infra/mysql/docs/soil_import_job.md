# `soil_import_job` / `soil_import_job_diff` 表设计说明

## 表用途

这两张表支撑“先预览差异，再确认导入”的后台流程。

- `soil_import_job`：记录一次导入任务的状态、进度、摘要与错误信息。
- `soil_import_job_diff`：记录预览阶段生成的差异快照。
- 真正写入事实表发生在管理员确认应用之后。

## 主键与关联关系

- `soil_import_job.job_id`：任务主键
- `soil_import_job_diff.diff_id`：差异明细主键
- `soil_import_job_diff.job_id -> soil_import_job.job_id`

## `soil_import_job` 字段说明

| 字段 | 类型 | 可空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `job_id` | `char(36)` | 否 | 无 | 导入任务唯一标识。 |
| `filename` | `varchar(255)` | 否 | 无 | 上传文件名。 |
| `requested_by_user_id` | `bigint` | 是 | `NULL` | 发起导入的用户 ID。 |
| `requested_by_username` | `varchar(64)` | 是 | `NULL` | 发起导入的用户名。 |
| `status` | `varchar(32)` | 否 | 无 | 任务状态，如 `previewing`、`ready`、`applying`、`succeeded`、`failed`。 |
| `apply_mode` | `varchar(16)` | 是 | `NULL` | 应用模式，当前为 `incremental` 或 `replace`。 |
| `processed_rows` | `int` | 否 | `0` | 当前阶段已处理行数。 |
| `total_rows` | `int` | 否 | `0` | 当前阶段总行数。 |
| `summary_json` | `json` | 是 | `NULL` | 预览摘要，包含有效、无效、新增、差异、删除等统计。 |
| `error_message` | `text` | 是 | `NULL` | 失败原因。 |
| `finished_at` | `datetime` | 是 | `NULL` | 当前阶段结束时间。 |
| `created_at` | `datetime` | 否 | `CURRENT_TIMESTAMP` | 创建时间。 |
| `updated_at` | `datetime` | 否 | `CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间。 |

## `soil_import_job_diff` 字段说明

| 字段 | 类型 | 可空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `diff_id` | `bigint` | 否 | `AUTO_INCREMENT` | 差异明细主键。 |
| `job_id` | `char(36)` | 否 | 无 | 所属导入任务。 |
| `diff_type` | `varchar(16)` | 否 | 无 | 差异类型：`create`、`update`、`unchanged`、`delete`、`invalid`。 |
| `id` | `varchar(64)` | 是 | `NULL` | 关联事实记录的 `id`。 |
| `source_row` | `int` | 是 | `NULL` | Excel 来源行号。 |
| `db_record_json` | `json` | 是 | `NULL` | 当前库内记录快照。 |
| `import_record_json` | `json` | 是 | `NULL` | 导入文件记录快照。 |
| `field_changes_json` | `json` | 是 | `NULL` | 字段变更摘要或无效原因。 |
| `created_at` | `datetime` | 否 | `CURRENT_TIMESTAMP` | 差异生成时间。 |

## 索引

- `idx_soil_import_job_status_created_at (status, created_at)`
- `idx_soil_import_job_diff_lookup (job_id, diff_type, diff_id)`

## 读写链路

- 写入：
  - `apps/web/lib/server/soilImportJobRepository.mjs`
- 读取：
  - `GET /api/admin/soil/import-jobs/[jobId]`
  - `GET /api/admin/soil/import-jobs/[jobId]/diff`

## 导入约定

- 预览阶段只产出 diff，不直接写 `fact_soil_moisture`。
- 应用阶段写入 `fact_soil_moisture` 后刷新 `region_alias` 的自动种子。
- 上传记录缺少 `id`、`sn`、`create_time` 时进入 `invalid`。
- 同一文件里如果 `id` 重复，预览阶段直接失败。
