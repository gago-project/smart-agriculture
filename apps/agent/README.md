# Soil Moisture Agent

当前只保留 deterministic `/chat-v2` 一套数据回答链路。

## 当前链路

`InputGuard` -> `TurnRouteDecisionService` -> `QueryProfileResolverService` -> `DataAnswerService`

## 核心原则

- 事实只来自 `fact_soil_moisture`
- 查询证据只走 `agent_query_log`
- 多轮追问只围绕 `TurnContext` 和 `QueryProfile`

## 文档导航

- `plans/1/README.md` - 当前查询治理索引
- `plans/1/9.query-profile-governance.md` - `/chat-v2` 查询治理说明
- `infra/mysql/docs/README.md` - 数据库设计入口
- `infra/mysql/docs/region-alias-resolution.md` - 地区别名解析
- `testdata/agent/soil-moisture/README.md` - 56 条正式验收入口
