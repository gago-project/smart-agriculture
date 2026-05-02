# `agent_query_log` 表设计说明

## 表作用

`agent_query_log` 是 Agent 查询审计表，用于记录一次真实查询从“用户问题”到“最终 SQL 审计结果”的完整上下文。

它回答的问题不是“用户说了什么”，而是：

- Agent 最终识别成什么意图；
- 生成了什么查询计划；
- 实际执行了什么 SQL；
- 查出了多少行；
- 返回给用户什么结果；
- 最终是正常结束还是走了兜底分支。

## 主键与关联关系

- 主键：`query_id`
- 当前没有外键约束
- `session_id` / `turn_id` 是前端本地会话标识，不依赖服务端会话表。

## 字段说明

### 轮次与上下文信息

| 字段 | 类型 | 为空 | 含义 |
| --- | --- | --- | --- |
| `query_id` | `varchar(64)` | 否 | 查询日志主键。 |
| `session_id` | `varchar(64)` | 否 | 浏览器本地生成的会话 ID，用于关联同一对话中的多轮问题。 |
| `turn_id` | `int` | 否 | 浏览器本地会话内的轮次编号。 |
| `request_text` | `text` | 是 | 用户原始输入文本。 |
| `response_text` | `text` | 是 | 最终返回给用户的回答文本。 |
| `input_type` | `varchar(32)` | 是 | 输入类型，例如业务直问、边界外输入、闲聊等。 |
| `intent` | `varchar(64)` | 是 | 识别后的业务意图。 |
| `answer_type` | `varchar(64)` | 是 | 回答类型。 |
| `final_status` | `varchar(64)` | 是 | Flow 最终结束状态，例如 `verified_end`、`fallback_end`。 |

### 查询计划与执行信息

| 字段 | 类型 | 为空 | 含义 |
| --- | --- | --- | --- |
| `query_type` | `varchar(64)` | 否 | 查询类型，例如概览、设备详情、异常查询。 |
| `query_plan_json` | `json` | 否 | 编译后的查询计划。 |
| `sql_fingerprint` | `varchar(255)` | 是 | SQL 模板指纹或标识。 |
| `executed_sql_text` | `text` | 是 | 实际执行的完整 SQL 审计文本。 |
| `time_range_json` | `json` | 否 | 查询时间范围。 |
| `filters_json` | `json` | 否 | 过滤条件集合。 |
| `group_by_json` | `json` | 是 | 分组字段。 |
| `metrics_json` | `json` | 是 | 聚合指标。 |
| `order_by_json` | `json` | 是 | 排序规则。 |
| `limit_size` | `int` | 是 | 返回条数限制。 |

### 结果与错误信息

| 字段 | 类型 | 为空 | 含义 |
| --- | --- | --- | --- |
| `row_count` | `int` | 否 | SQL 实际返回的行数。 |
| `executed_result_json` | `json` | 是 | SQL 完整执行结果 JSON。 |
| `source_files_json` | `json` | 是 | 涉及的数据源文件列表。 |
| `status` | `varchar(32)` | 否 | 执行状态，例如 `success`、`empty`、`failed`、`blocked`。 |
| `error_message` | `text` | 是 | 执行错误信息。 |
| `created_at` | `datetime` | 否 | 日志写入时间。 |

## 索引与约束

- `PRIMARY KEY (query_id)`

### 当前二级索引

| 索引名 | 字段 | 作用 |
| --- | --- | --- |
| `idx_aql_session_turn` | `session_id, turn_id` | 追踪同一会话多轮查询。 |
| `idx_aql_created_at` | `created_at` | 支撑按时间倒序分页。 |
| `idx_aql_query_type_created_at` | `query_type, created_at` | 支撑按查询类型筛选后排序。 |
| `idx_aql_status_created_at` | `status, created_at` | 支撑按执行状态筛选。 |

## 实际读写链路

### 写入来源

- `apps/agent/app/repositories/query_log_repository.py`
  - `append()`
  - `insert_many()`

写入时会对 JSON 字段进行序列化，并在 `query_id` 已存在时执行更新。

### 读取来源

- `apps/web/lib/server/agentLogRepository.mjs`
  - 先分页读取 `query_id`
  - 再按 `query_id` 批量取详情
  - 对 JSON 字段做反序列化

## 当前迁移与兼容处理

`infra/mysql/init/001_init_tables.sql` 里除了建表，还包含了兼容旧库的辅助过程：

- `ensure_column(...)`：为旧库补齐 `request_text`、`response_text`、`input_type`、`intent`、`answer_type`、`final_status`、`executed_sql_text`、`executed_result_json`
- `drop_column_if_exists(...)`：删除废弃的 `result_preview_json`

这说明该表是迭代演进中的重点审计表。

## JSON 字段说明

- `query_plan_json`：编排后的查询计划事实
- `time_range_json`：时间窗
- `filters_json`：过滤条件
- `group_by_json`：分组维度
- `metrics_json`：聚合指标
- `order_by_json`：排序表达
- `executed_result_json`：完整结果数据
- `source_files_json`：来源文件列表

这些字段都由应用层负责序列化/反序列化，数据库只负责存储。

## 注意事项

- 这张表可能比较大，因为它同时保存了 SQL 文本和完整结果 JSON。
- `status` 与 `final_status` 含义不同：前者更偏执行结果，后者更偏 Flow 结束节点状态。
- 当前不再使用 `result_preview_json`；排查问题时应优先看 `executed_result_json`。
