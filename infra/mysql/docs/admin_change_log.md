# `admin_change_log` 表设计说明

## 表作用

`admin_change_log` 设计用于记录后台管理动作的审计信息，典型场景包括：

- 后台修改事实数据；
- 后台删除记录；
- 后台修改规则或模板。

它和 `agent_query_log` 的职责不同：前者记录“管理端改了什么”，后者记录“Agent 查了什么”。

## 主键与关联关系

- 主键：`id`
- 当前没有外键约束

## 字段说明

| 字段 | 类型 | 为空 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| `id` | `bigint` | 否 | 无 | 审计记录主键。 |
| `operator_user_id` | `bigint` | 是 | `NULL` | 操作人用户 ID，通常关联后台登录用户。 |
| `operator_username` | `varchar(64)` | 是 | `NULL` | 操作人用户名，便于审计时直接阅读。 |
| `operation` | `varchar(64)` | 否 | 无 | 操作类型，例如新增、修改、删除、启停。 |
| `target_table` | `varchar(128)` | 否 | 无 | 被操作的表名。 |
| `target_id` | `varchar(128)` | 是 | `NULL` | 被操作对象的主键值或业务 ID。 |
| `before_json` | `json` | 是 | `NULL` | 变更前快照。 |
| `after_json` | `json` | 是 | `NULL` | 变更后快照。 |
| `created_at` | `datetime` | 否 | 无 | 操作发生时间。 |

## 索引与约束

- `PRIMARY KEY (id)`
- 当前 DDL 中没有额外二级索引。

## 实际读写链路

### 设计目标中的写入场景

- 后台修改 `fact_soil_moisture`
- 后台删除 `fact_soil_moisture`
- 后台修改 `metric_rule`
- 后台修改 `warning_template`

### 当前仓库状态

- 表已经存在于 DDL 中。
- 但当前仓库内尚未看到正式落库到 `admin_change_log` 的写入实现。
- 也就是说，这张表目前更像是“已建好但待接入的审计能力占位表”。

## JSON 字段说明

- `before_json`：记录操作前完整或关键字段快照。
- `after_json`：记录操作后完整或关键字段快照。

如果只记录单字段修改，仍建议保存完整业务快照，这样回溯更直接。

## 注意事项

- 由于当前没有写入逻辑，不能把它当作已经可用的审计事实来源。
- 若后续正式启用后台审计，建议优先保证：
  - 关键写操作都落库；
  - `before_json` / `after_json` 结构稳定；
  - 与 `auth_user` 的操作人信息闭环。
