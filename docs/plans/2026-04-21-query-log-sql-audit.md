# Query Log SQL Audit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将工作台中的“开发日志”统一改为“查询日志”，并为 `agent_query_log` 增加可执行审计 SQL 记录能力，同时同步更新权威 plans 文档，确保实现与设计一致。

**Architecture:** 在 Agent 实际执行 SQL 的仓库层生成本次查询的完整审计 SQL 文本，并沿 `query_result -> query_log_entry -> agent_query_log -> web query logs API -> 查询日志页` 这条链路向上透传。现有 `sql_fingerprint` 保留用于模板标识，新增 `executed_sql_text` 用于精确排障；前端列表页展示 SQL 摘要并支持查看完整 SQL。

**Tech Stack:** Python、Next.js、MySQL、Node test、unittest、仓库内 plans Markdown

---

### Task 1: 补齐失败测试与计划文档约束

**Files:**
- Modify: `apps/web/tests/file-contract.test.mjs`
- Modify: `apps/web/tests/db-schema-contract.test.mjs`
- Modify: `apps/agent/tests/test_query_log_repository_unittest.py`
- Modify: `apps/agent/tests/test_agent_flow_behavior_unittest.py`

**Step 1: 写失败测试**

- 断言工作台入口文案从 `开发日志` 改为 `查询日志`
- 断言 `agent_query_log` 表包含 `executed_sql_text`
- 断言查询日志落库时会写入完整 SQL
- 断言成功查询生成的日志对象包含 `executed_sql_text`

**Step 2: 运行测试确认失败**

Run: `npm --prefix apps/web test`
Expected: 与新文案 / schema 字段断言相关测试失败

Run: `PYTHONPATH=apps/agent .venv/bin/python -m unittest apps.agent.tests.test_query_log_repository_unittest apps.agent.tests.test_agent_flow_behavior_unittest -v`
Expected: 与 `executed_sql_text` 断言相关测试失败

### Task 2: 实现 Agent 侧 SQL 审计字段

**Files:**
- Modify: `infra/mysql/init/001_init_tables.sql`
- Modify: `apps/agent/app/repositories/soil_repository.py`
- Modify: `apps/agent/app/services/soil_query_service.py`
- Modify: `apps/agent/app/repositories/query_log_repository.py`

**Step 1: 在 schema 中新增字段**

- 为 `agent_query_log` 增加 `executed_sql_text TEXT NULL`
- 若初始化脚本已有 `ensure_column` 机制，则补一条幂等加列语句

**Step 2: 在仓库层生成审计 SQL**

- 在 `soil_repository.py` 为固定查询构建可执行 SQL 文本
- 使用安全的字符串转义，仅用于审计日志展示，不参与执行
- 将该文本附加到查询结果元数据中

**Step 3: 透传到查询日志落库**

- `soil_query_service.build_query_log_entry()` 将 `executed_sql_text` 带入日志 entry
- `query_log_repository.py` 规范化并写入 MySQL

### Task 3: 实现 Web 侧查询日志文案与 SQL 展示

**Files:**
- Modify: `apps/web/workspace/App.tsx`
- Modify: `apps/web/workspace/components/AgentLogPage.tsx`
- Modify: `apps/web/workspace/services/agentLogApi.ts`
- Modify: `apps/web/lib/server/agentLogRepository.mjs`

**Step 1: 统一文案**

- 将入口按钮、页面标题、可访问性标签中的 `开发日志` 统一改为 `查询日志`

**Step 2: 返回并展示 SQL 字段**

- API 类型补 `executed_sql_text`
- 服务端仓库查询 `agent_query_log.executed_sql_text`
- 页面展示 SQL 摘要，并提供完整 SQL 查看区域

### Task 4: 同步更新权威 plans 文档

**Files:**
- Modify: `apps/agent/plans/1/1.2026-04-20-soil-moisture-agent-plan.md`

**Step 1: 更新表结构定义**

- 在 `agent_query_log` 表设计中补充 `executed_sql_text`
- 明确 `sql_fingerprint` 与 `executed_sql_text` 的职责差异

**Step 2: 更新日志要求描述**

- 说明查询日志应同时记录模板标识与本次可执行 SQL 文本

### Task 5: 运行验证

**Files:**
- Modify: 无

**Step 1: 运行 Web 测试**

Run: `npm --prefix apps/web test`
Expected: PASS

**Step 2: 运行 Agent 定向测试**

Run: `PYTHONPATH=apps/agent .venv/bin/python -m unittest apps.agent.tests.test_query_log_repository_unittest apps.agent.tests.test_agent_flow_behavior_unittest -v`
Expected: PASS

**Step 3: 如有需要补充 schema 合约验证**

Run: `npm --prefix apps/web test -- --test-name-pattern="agent_query_log|query logs|developer workspace"`
Expected: PASS
