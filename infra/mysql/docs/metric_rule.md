# `metric_rule` 表设计说明

## 表作用

`metric_rule` 用于保存运行时规则配置，当前主要承载两类规则：

- 墒情异常分析规则；
- 墒情预警规则。

它的目标是把规则从硬编码中抽出来，允许初始化脚本或后台配置统一维护。

## 主键与关联关系

- 主键：`rule_code`
- 当前没有外键依赖其他表

## 字段说明

| 字段 | 类型 | 为空 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| `rule_code` | `varchar(64)` | 否 | 无 | 规则唯一编码，例如 `soil_warning_v1`。 |
| `rule_name` | `varchar(128)` | 否 | 无 | 规则名称，面向配置页和运维排查。 |
| `rule_scope` | `varchar(64)` | 否 | 无 | 规则作用域，用于标识业务域。当前主要是 `soil_moisture`。 |
| `rule_definition_json` | `json` | 否 | 无 | 规则定义主体，包含条件、优先级、模板或其他执行参数。 |
| `enabled` | `tinyint` | 否 | `1` | 是否启用，`1` 为启用，`0` 为停用。 |
| `updated_at` | `datetime` | 否 | 无 | 规则最后更新时间。 |

## 索引与约束

- `PRIMARY KEY (rule_code)`
- 二级索引：`idx_metric_rule_scope_enabled (enabled, rule_scope, updated_at)`

这个索引主要服务于“按业务域读取当前启用规则”的场景。

## 当前初始化数据

`infra/mysql/init/002_insert_data.sql` 当前会写入：

- `soil_anomaly_v1`：墒情异常分析规则；
- `soil_warning_v1`：墒情预警规则。

其中 `rule_definition_json` 中已经包含：

- 条件表达式；
- 优先级语义；
- 模板输出配置；
- 是否允许模板输出等运行参数。

## 实际读写链路

### 写入来源

- `infra/mysql/init/002_insert_data.sql`：初始化规则数据。
- `apps/web/lib/server/soilAdminRepository.mjs` 的 `patchRuleConfig()`：后台修改规则 JSON、启停状态和更新时间。

### 读取来源

- `apps/web/lib/server/soilAdminRepository.mjs` 的 `listRuleConfig()`：后台规则配置页读取规则列表。
- `apps/agent/plans/1/1.2026-04-20-soil-moisture-agent-plan.md` 把它定义为运行时规则权威来源。

## JSON 字段说明

`rule_definition_json` 没有在数据库层进一步拆表，当前设计刻意保持灵活。现阶段它通常包含：

- `scope`：规则适用范围；
- `rules`：规则列表；
- `condition`：触发条件表达式；
- `warning_level` / `status`：规则命中的输出标签；
- `priority`：同类规则优先级；
- `template`：模板输出配置。

## 注意事项

- 当前规则是“表内 JSON + 应用层解释执行”的模式，不是多表标准化建模。
- 如果未来规则复杂度大幅提升，才需要再评估是否拆出规则项、条件项、版本表。
- 修改该表内容会直接影响后台规则展示和后续 Agent 规则执行口径，应做好变更审计。
