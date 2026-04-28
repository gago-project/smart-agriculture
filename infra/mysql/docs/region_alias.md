# `region_alias` 表设计说明

## 表用途

`region_alias` 保存地区别名到标准名称的映射，服务于 Agent 的地区解析。

- 当前只覆盖两级地区：`city`、`county`。
- 表内不承载乡镇级语义。
- 既支持从事实表自动生成，也支持人工补充固定别名。

## 主键与索引

- 主键：`PRIMARY KEY (id)`
- 唯一约束：`uk_region_alias_mapping (alias_name, canonical_name, region_level, enabled)`
- 查询索引：`idx_region_alias_lookup (enabled, alias_name, region_level)`

## 字段说明

| 字段 | 类型 | 可空 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | `bigint` | 否 | `AUTO_INCREMENT` | 自增主键。 |
| `alias_name` | `varchar(64)` | 否 | 无 | 用户可能输入的简称、口语或轻度变体。 |
| `canonical_name` | `varchar(64)` | 否 | 无 | 规范后的标准地区名称。 |
| `region_level` | `varchar(16)` | 否 | 无 | 地区层级，当前只使用 `city` 或 `county`。 |
| `parent_city_name` | `varchar(64)` | 是 | `NULL` | 区县别名对应的父级市，用于歧义消解。 |
| `alias_source` | `varchar(32)` | 否 | 无 | 别名来源，如 `generated_fact`、`canonical`、`manual`。 |
| `enabled` | `tinyint` | 否 | `1` | 是否启用。 |
| `created_at` | `datetime` | 否 | `CURRENT_TIMESTAMP` | 创建时间。 |
| `updated_at` | `datetime` | 否 | `CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间。 |

## 读写链路

- 写入：
  - `infra/mysql/init/003_insert_soil_data.sql`
  - `apps/web/lib/server/regionAliasSeed.mjs`
  - `apps/web/scripts/generate-region-alias-seed.mjs`
- 读取：
  - `apps/agent/app/repositories/soil_repository.py`
  - `apps/agent/app/services/parameter_resolver_service.py`

## 业务约定

- `region_level=city` 时，`parent_city_name` 通常为空。
- `region_level=county` 时，允许带上所属 `city`，帮助处理重名区县。
- 多候选场景必须进入澄清，不允许直接猜测。
- 若 LLM 把区县名填进 `city` 或把市名填进 `county`，仅在候选唯一时允许自动纠正字段。
- `city` 与 `county` 同时存在时，应校验 `county.parent_city_name` 与 `city` 是否一致；不一致时必须澄清。
