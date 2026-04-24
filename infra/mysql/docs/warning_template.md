# `warning_template` 表设计说明

## 表用途

`warning_template` 保存受控预警模板，把模板文本与代码逻辑分离。

- 规则引擎负责判断是否触发以及输出哪个等级。
- 模板负责最终文案骨架。
- 当前模板字段只允许使用现有运行时契约字段。

## 主键与边界

- 主键：`PRIMARY KEY (template_id)`
- 当前没有外键
- 模板允许变更文案，但不允许绕开事实字段自由发挥

## 字段说明

| 字段 | 类型 | 可空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `template_id` | `varchar(64)` | 否 | 无 | 模板唯一标识。 |
| `domain` | `varchar(32)` | 否 | 无 | 所属业务域，当前为 `soil_moisture`。 |
| `warning_type` | `varchar(64)` | 否 | 无 | 模板类型，当前用于墒情预警。 |
| `audience` | `varchar(64)` | 否 | 无 | 模板受众，例如 `general`。 |
| `template_name` | `varchar(128)` | 否 | 无 | 模板名称。 |
| `template_text` | `text` | 否 | 无 | 模板正文，允许包含受控占位符。 |
| `required_fields_json` | `json` | 否 | 无 | 渲染模板必须提供的字段列表。 |
| `version` | `varchar(64)` | 否 | 无 | 模板版本号。 |
| `enabled` | `tinyint` | 否 | `1` | 是否启用。 |
| `created_at` | `datetime` | 否 | 无 | 创建时间。 |
| `updated_at` | `datetime` | 否 | 无 | 更新时间。 |

## 当前模板占位符

当前初始化模板只使用以下字段：

- `year`
- `month`
- `day`
- `hour`
- `city`
- `county`
- `sn`
- `water20cm`
- `warning_level`

## 读写链路

- 写入：
  - `infra/mysql/init/002_insert_data.sql`
  - `apps/web/lib/server/soilAdminRepository.mjs`
- 读取：
  - `apps/web/lib/server/soilAdminRepository.mjs`
  - `apps/agent/app/templates/soil_warning.j2`

## 注意事项

- 模板渲染缺字段时必须失败并走受控降级。
- `required_fields_json` 只描述渲染前置条件，不存放具体值。
