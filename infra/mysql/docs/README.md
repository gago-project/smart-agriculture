# Smart Agriculture 数据库文档

本目录用于存放 `smart_agriculture` 库的结构说明文档，目标是把数据库设计从 Agent 能力方案中独立出来，形成单独维护的数据库文档入口。

## 权威来源

- 建表与索引：`infra/mysql/init/001_init_tables.sql`
- 业务初始化数据：`infra/mysql/init/002_insert_data.sql`
- 墒情事实与地区别名种子：`infra/mysql/init/003_insert_soil_data.sql`

如表结构与本目录说明不一致，以 SQL 初始化脚本为准；文档应随后同步更新。

## 目录索引

### 核心业务数据

- [`fact_soil_moisture.md`](./fact_soil_moisture.md)：墒情事实表，Agent 与后台查询的事实来源。
- [`etl_import_batch.md`](./etl_import_batch.md)：导入批次表，记录每次 Excel 或后台导入的批次状态。
- [`soil_import_job.md`](./soil_import_job.md)：后台 Excel 导入预览任务与 diff 快照表，支撑轮询进度、预览确认和二次确认覆盖。
- [`region_alias.md`](./region_alias.md)：地区别名映射表，支持简称补全、静态种子和多候选歧义处理。

### 规则与模板

- [`metric_rule.md`](./metric_rule.md)：运行时规则配置表，承载异常分析和墒情预警规则。
- [`warning_template.md`](./warning_template.md)：预警模板表，承载标准文案和必填字段列表。

### 审计与安全

- [`agent_query_log.md`](./agent_query_log.md)：Agent 查询日志表，用于审计与排障。
- [`admin_change_log.md`](./admin_change_log.md)：管理操作审计表，用于记录后台变更。
- [`auth_user.md`](./auth_user.md)：登录用户表。
- [`auth_session.md`](./auth_session.md)：登录会话表。

### 配套设计

- [`region-alias-resolution.md`](./region-alias-resolution.md)：地区别名生成与解析设计，说明 `region_alias` 如何参与简称补全、轻度模糊匹配与澄清。

## 维护原则

- 表结构变化后，必须同步更新对应表文档。
- 文档按“表职责 → 字段 → 索引/约束 → 实际读写链路 → 注意事项”的顺序描述。
- 只记录当前仓库内真实存在的表和字段；未来增强方案应明确标注为“未落地”。
