# Smart Agriculture 数据库文档

本目录统一维护 `smart_agriculture` 的数据库设计说明。

## 当前原则

- 原始 Excel 字段名是墒情事实表唯一真相。
- `create_time` 是当前查询执行统一使用的时间列。
- 墒情域不再保留批次语义文档与批次表说明。
- 文档必须与 `infra/mysql/init/001_init_tables.sql` 保持一致。

## 权威来源

- 建表与索引：`infra/mysql/init/001_init_tables.sql`
- 规则与模板初始化：`infra/mysql/init/002_insert_data.sql`
- 墒情事实与地区别名种子：`infra/mysql/init/003_insert_soil_data.sql`

## 表文档

- [`fact_soil_moisture.md`](./fact_soil_moisture.md)
- [`soil_import_job.md`](./soil_import_job.md)
- [`region_alias.md`](./region_alias.md)
- [`metric_rule.md`](./metric_rule.md)
- [`warning_template.md`](./warning_template.md)
- [`agent_query_log.md`](./agent_query_log.md)
- [`admin_change_log.md`](./admin_change_log.md)
- [`auth_user.md`](./auth_user.md)
- [`auth_session.md`](./auth_session.md)

## 配套设计

- [`region-alias-resolution.md`](./region-alias-resolution.md)

## 维护要求

- 先改 DDL，再同步文档。
- 字段改名、增删字段、索引变更后必须同步更新对应文档。
- 运行时临时计算字段不能写进事实表字段说明。
