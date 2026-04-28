# 地区别名解析与 `region_alias` 使用设计

## 目标

让用户输入的自然语言地区词稳定落到 `city` / `county` 两级标准名称。

- 支持全称自映射：`南京市 -> 南京市`
- 支持常见简称：`南京 -> 南京市`、`如东 -> 如东县`
- 支持唯一高置信轻度错别字：`苏洲 -> 苏州市`
- 多候选时必须澄清，不自动猜

## 种子来源

当前静态种子由 `fact_soil_moisture` 的 `city`、`county` 去重生成：

- 生成文件：`apps/web/lib/server/regionAliasSeed.mjs`
- 脚本入口：`apps/web/scripts/generate-region-alias-seed.mjs`
- 初始化落库：`infra/mysql/init/003_insert_soil_data.sql`
- 这些结果会作为静态种子写回初始化 SQL

## 生成规则

- 全称自映射：保留原始 `city`、`county`
- 去后缀简称：
  - `南京市 -> 南京`
  - `如东县 -> 如东`
- 区县别名保留 `parent_city_name`，用于重名区县消歧

## 解析顺序

1. 精确命中标准名
2. 精确命中别名
3. 唯一高置信轻度模糊匹配（按一编辑距离控制）
4. 唯一简称 / 前缀匹配
5. 若命中层级与字段不一致，但候选唯一，则自动纠正到正确字段
6. 多候选则澄清

## 一致性规则

- 用户只提一个地区词时，只填一个最有把握的字段。
- 用户同时给出 `X市Y县/区` 时，`city`、`county` 都填写。
- `city` 与 `county` 同时存在时，必须用 `parent_city_name` 校验父级市一致性；不一致则澄清。
- `query_soil_comparison` 内部解析结果保留 `canonical_name`、`level`、`parent_city_name`，执行层按 level 直接走对应 SQL 分支。

## 验收样例

- `南京最近一个月的数据` -> `city=南京市`
- `南通最近7天墒情怎么样` -> `city=南通市`
- `如东最近怎么样` -> `county=如东县`
- `苏洲最近一个月的数据` -> `city=苏州市`
- `新区最近怎么样` -> 多候选时澄清

## 边界

- 当前不处理乡镇级别名。
- 当前不引入行政区维表或全文检索。
- 如果后续跨省重名增多，再评估单独的行政区维表方案。
