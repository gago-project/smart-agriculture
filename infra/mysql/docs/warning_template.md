# `warning_template` 表设计说明

## 表作用

`warning_template` 用于保存标准预警模板，把最终输出文案从规则或代码里独立出来。

当前系统只有一类土壤墒情预警模板，但仍单独建表，方便后续：

- 多模板版本并存；
- 后台调整文案；
- 按业务域或受众切换模板。

## 主键与关联关系

- 主键：`template_id`
- 当前没有外键约束

## 字段说明

| 字段 | 类型 | 为空 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| `template_id` | `varchar(64)` | 否 | 无 | 模板唯一标识。 |
| `domain` | `varchar(32)` | 否 | 无 | 模板所属业务域，例如 `soil_moisture`。 |
| `warning_type` | `varchar(64)` | 否 | 无 | 预警类型。 |
| `audience` | `varchar(64)` | 否 | 无 | 模板目标受众，例如通用、管理侧、农户侧。 |
| `template_name` | `varchar(128)` | 否 | 无 | 模板展示名称。 |
| `template_text` | `text` | 否 | 无 | 模板正文，通常包含占位符。 |
| `required_fields_json` | `json` | 否 | 无 | 渲染该模板必须提供的字段列表。 |
| `version` | `varchar(64)` | 否 | 无 | 模板版本号。 |
| `enabled` | `tinyint` | 否 | `1` | 是否启用。 |
| `created_at` | `datetime` | 否 | 无 | 创建时间。 |
| `updated_at` | `datetime` | 否 | 无 | 更新时间。 |

## 索引与约束

- `PRIMARY KEY (template_id)`
- 当前 DDL 中没有额外二级索引。

## 当前初始化数据

`infra/mysql/init/002_insert_data.sql` 当前会写入一条模板：

- `template_id = soil_warning_template_v1`
- 业务域：`soil_moisture`
- 预警类型：`soil_warning`
- 受众：`general`
- 版本：`v1`

模板正文会使用以下关键占位符：

- `year`
- `month`
- `day`
- `hour`
- `city_name`
- `county_name`
- `device_sn`
- `water20cm`
- `warning_level`

## 实际读写链路

### 写入来源

- `infra/mysql/init/002_insert_data.sql`：初始化模板。
- `apps/web/lib/server/soilAdminRepository.mjs` 的 `patchRuleConfig()`：后台更新 `template_text` 和 `updated_at`。

### 读取来源

- `apps/web/lib/server/soilAdminRepository.mjs` 的 `listRuleConfig()`：后台配置页读取模板列表。

### 当前实现现状

- Python Agent 仓库 `apps/agent/app/repositories/soil_repository.py` 当前 `warning_template_text()` 返回的是代码内置默认模板文本。
- 也就是说，这张表已经是后台配置事实来源，但 Agent 运行时模板读取尚未完全切换到数据库。

## JSON 字段说明

- `required_fields_json`：模板渲染前必须具备的字段名数组。

这个字段的作用不是保存渲染值，而是保存“渲染前置条件”。

## 注意事项

- `template_text` 是可配置内容，但不意味着可以绕开事实字段直接自由生成文案。
- 模板变更通常需要和 `metric_rule` 的规则输出字段保持一致，否则会出现渲染缺字段。
