# `soil_import_job` 与 `soil_import_job_diff` 表设计说明

## 表作用

这两张表支撑墒情管理页面的 Excel “先预览 diff，再确认导入”流程。

- `soil_import_job` 保存导入任务状态、进度、摘要和错误信息。
- `soil_import_job_diff` 保存一次上传解析后的差异快照，页面按类型分页查看。
- 真正写入 `fact_soil_moisture` 只发生在管理员点击“增量添加”或“全量覆盖”之后。

## 主键与关联关系

- `soil_import_job.job_id`：导入任务主键，使用 UUID。
- `soil_import_job_diff.diff_id`：diff 明细自增主键。
- `soil_import_job_diff.job_id -> soil_import_job.job_id`：一条任务对应多条 diff 明细。

## 字段说明

### `soil_import_job`

| 字段 | 类型 | 为空 | 含义 |
| --- | --- | --- | --- |
| `job_id` | `char(36)` | 否 | 导入任务 ID。 |
| `filename` | `varchar(255)` | 否 | 上传文件名。 |
| `requested_by_user_id` | `bigint` | 是 | 发起导入的用户 ID。 |
| `requested_by_username` | `varchar(64)` | 是 | 发起导入的用户名。 |
| `status` | `varchar(32)` | 否 | 任务状态，当前使用 `previewing` / `ready` / `applying` / `succeeded` / `failed`。 |
| `apply_mode` | `varchar(16)` | 是 | 实际应用模式，当前使用 `incremental` / `replace`。 |
| `processed_rows` | `int` | 否 | 当前已处理行数，用于页面轮询进度。 |
| `total_rows` | `int` | 否 | 当前阶段总处理行数。 |
| `summary_json` | `json` | 是 | 预览摘要，包括原始行、有效行、无效行、新增、有差异、无变化、覆盖会删除和可应用行数。 |
| `error_message` | `text` | 是 | 预览或应用失败时的错误摘要。 |
| `finished_at` | `datetime` | 是 | 当前阶段结束时间。 |
| `created_at` | `datetime` | 否 | 任务创建时间。 |
| `updated_at` | `datetime` | 否 | 任务更新时间。 |

### `soil_import_job_diff`

| 字段 | 类型 | 为空 | 含义 |
| --- | --- | --- | --- |
| `diff_id` | `bigint` | 否 | diff 明细自增 ID。 |
| `job_id` | `char(36)` | 否 | 所属导入任务。 |
| `diff_type` | `varchar(16)` | 否 | 差异类型：`create` / `update` / `unchanged` / `delete` / `invalid`。 |
| `record_id` | `varchar(64)` | 是 | 关联的事实记录 ID。 |
| `source_row` | `int` | 是 | Excel 来源行号。 |
| `db_record_json` | `json` | 是 | 当前库内记录快照。 |
| `import_record_json` | `json` | 是 | 上传文件解析后的记录快照。 |
| `field_changes_json` | `json` | 是 | 字段变化摘要或无效原因。 |
| `created_at` | `datetime` | 否 | diff 生成时间。 |

## 索引与约束

| 索引名 | 字段 | 作用 |
| --- | --- | --- |
| `idx_soil_import_job_status_created_at` | `status, created_at` | 支撑按任务状态和时间排查。 |
| `idx_soil_import_job_diff_lookup` | `job_id, diff_type, diff_id` | 支撑页面按任务、类型分页查询 diff。 |

## 实际读写链路

### 写入来源

- `POST /api/admin/soil/import-jobs`：创建任务，后台解析 Excel 并写入 diff 快照。
- `POST /api/admin/soil/import-jobs/[jobId]/apply`：应用任务，写入 `fact_soil_moisture` 与 `etl_import_batch`。

### 读取来源

- `GET /api/admin/soil/import-jobs/[jobId]`：页面轮询状态与 `processed_rows / total_rows`。
- `GET /api/admin/soil/import-jobs/[jobId]/diff`：页面分页展示 diff 样本。

## 导入语义

- `incremental`：只插入 `diff_type='create'` 的记录，不更新已有 `record_id`。
- `replace`：必须二次确认，先清空当前事实表，再写入本次预览里的全部有效记录。
- 上传文件内若存在重复 `record_id`，预览任务直接失败，不自动去重或覆盖。

## 注意事项

- `soil_import_job_diff` 是预览快照，不代表事实表已经变更。
- 页面进度来自 `processed_rows / total_rows` 轮询，不使用 WebSocket 或 SSE。
- 应用成功后会刷新 `region_alias` 的 `generated_fact` 别名，让 Agent 地区解析与最新事实表保持一致。
