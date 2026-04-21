# `region_alias` 表设计说明

## 表作用

`region_alias` 用于保存“地区别名 → 标准地区名”的映射关系，服务于地区简称补全、静态别名种子和多候选歧义处理。

它存在的原因是：用户经常不会输入数据库里的全称地区，例如：

- `南京`，实际想查 `南京市`
- `如东`，实际想查 `如东县`

通过这张表，系统可以在 SQL 执行前把自然语言中的地区短语统一规范化。

## 主键与关联关系

- 主键：`id`
- 当前没有外键依赖到行政区维表或事实表

这是有意设计：别名表既可以来自事实表去重，也可以来自人工补充，不强依赖某一张维表。

## 字段说明

| 字段 | 类型 | 为空 | 默认值 | 含义 |
| --- | --- | --- | --- | --- |
| `id` | `bigint` | 否 | `AUTO_INCREMENT` | 自增主键。 |
| `alias_name` | `varchar(64)` | 否 | 无 | 用户可能输入的别名、简称或口语名称。 |
| `canonical_name` | `varchar(64)` | 否 | 无 | 规范后的标准地区名称。 |
| `region_level` | `varchar(16)` | 否 | 无 | 地区层级，当前使用 `city` / `county` / `town`。 |
| `parent_city_name` | `varchar(64)` | 是 | `NULL` | 父级市名称，用于约束区县或乡镇归属。 |
| `parent_county_name` | `varchar(64)` | 是 | `NULL` | 父级区县名称，主要用于乡镇别名歧义消解。 |
| `alias_source` | `varchar(32)` | 否 | 无 | 别名来源，例如从事实表生成、人工补充、规范全称自映射。 |
| `enabled` | `tinyint` | 否 | `1` | 是否启用。 |
| `created_at` | `datetime` | 否 | `CURRENT_TIMESTAMP` | 创建时间。 |
| `updated_at` | `datetime` | 否 | `CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` | 更新时间。 |

## 索引与约束

### 主键与唯一约束

- `PRIMARY KEY (id)`
- `UNIQUE KEY uk_region_alias_mapping (alias_name, canonical_name, region_level, enabled)`

这个唯一约束的含义是：同一条启用状态下，不能出现完全相同的别名映射记录。

### 查询索引

| 索引名 | 字段 | 作用 |
| --- | --- | --- |
| `idx_region_alias_lookup` | `enabled, alias_name, region_level` | 支撑按启用状态 + 别名 + 层级快速查找映射。 |

## 实际读写链路

### 写入来源

- `infra/mysql/init/003_insert_soil_data.sql`：保存生成后的静态别名种子。
- `apps/web/lib/server/regionAliasSeed.mjs`：生成并输出 SQL 种子块。
- `apps/web/scripts/generate-region-alias-seed.mjs`：从当前事实表生成静态别名 SQL。

### 读取来源

- `apps/agent/app/repositories/soil_repository.py` 的 `region_alias_rows()`：读取启用中的别名映射。
- `apps/agent/app/services/region_service.py`：基于这些映射完成简称补全、候选排序和歧义判断。

## 当前来源值约定

仓库中已经出现或明确使用的 `alias_source` 包括：

- `generated_fact`：从 `fact_soil_moisture` 去重后自动生成；
- `canonical`：规范全称自映射；
- `manual`：人工维护补充，代码中已为该优先级预留判断。

## 注意事项

- 一条别名可能对应多个标准地区，因此系统必须允许“多候选但不自动猜”的设计。
- 当前表没有强制外键到地区维表，这是为了兼容从事实表去重生成和后续人工补充两种来源。
- `enabled` 被纳入唯一键，意味着一条映射可通过启停实现“保留历史、仅切换有效版本”。
