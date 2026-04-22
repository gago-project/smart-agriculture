# Query Log Full Result JSON Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将查询日志从“结果预览”升级为“完整 SQL 查询结果”记录与展示，并移除 `result_preview_json` 的旧设计，保证库表、代码、测试与 plans 一致。

**Architecture:** 用一个语义明确的新字段承载完整执行结果 JSON，替代现有 `result_preview_json`。Agent 查询执行完成后，将完整 `query_result` 的可展示部分写入该字段；Web 查询日志保留“完整结果可查看”的能力，但为了避免列表接口响应过大，列表页接口只返回轻量摘要字段，完整 SQL 与完整结果 JSON 通过单条详情接口按需加载。plans 中同步移除“预览”语义。除这次替换外，查询日志表既有的请求/回答与路由上下文字段（`request_text`、`response_text`、`input_type`、`intent`、`answer_type`、`final_status`）继续保留，不在本计划中删除。

**Tech Stack:** Python、Next.js、MySQL、Node test、unittest、Markdown plans

---

### Task 1: 写失败测试

**Files:**
- Modify: `apps/web/tests/db-schema-contract.test.mjs`
- Modify: `apps/agent/tests/test_query_log_repository_unittest.py`
- Modify: `apps/agent/tests/test_agent_flow_behavior_unittest.py`

**Step 1: 更新 schema 合约测试**

- 断言 `agent_query_log` 包含新的完整结果字段
- 断言不再要求 `result_preview_json`

**Step 2: 更新 Agent 落库测试**

- 断言查询日志写入完整结果字段
- 断言参数序列化顺序与新 schema 对齐

**Step 3: 更新行为测试**

- 断言成功查询的日志对象带完整结果字段

### Task 2: 替换后端日志字段

**Files:**
- Modify: `infra/mysql/init/001_init_tables.sql`
- Modify: `apps/agent/app/services/soil_query_service.py`
- Modify: `apps/agent/app/repositories/query_log_repository.py`
- Modify: `apps/agent/app/repositories/soil_repository.py`

**Step 1: 修改表结构**

- 新增完整结果 JSON 字段
- 移除 `result_preview_json` 的 schema 设计
- 保持幂等加列/清理逻辑
- 不改动既有的请求/回答与路由上下文字段

**Step 2: 更新查询日志构造**

- 停止生成 `result_preview_json`
- 改为生成语义明确的完整结果 JSON 字段

**Step 3: 更新落库**

- `query_log_repository.py` 改写 insert/update 的字段列表与序列化逻辑

### Task 3: 更新 Web 查询日志接口与页面

**Files:**
- Modify: `apps/web/lib/server/agentLogRepository.mjs`
- Modify: `apps/web/workspace/services/agentLogApi.ts`
- Modify: `apps/web/workspace/components/AgentLogPage.tsx`

**Step 1: 更新服务端返回结构**

- 停止返回 `result_preview_json`
- 列表接口仅返回轻量字段
- 新增单条详情接口返回完整结果字段

**Step 2: 更新页面展示**

- 为每条日志增加“执行结果”展示
- 使用可展开的 JSON 展示方式
- 展开时按需请求完整 SQL 与完整结果

### Task 4: 清理权威 plans 文档

**Files:**
- Modify: `apps/agent/plans/1/1.2026-04-20-soil-moisture-agent-plan.md`

**Step 1: 更新表结构设计**

- 删除 `result_preview_json` 的设计描述
- 增加完整结果字段与中文说明

**Step 2: 更新日志语义**

- 明确开发阶段查询日志记录完整 SQL 结果

### Task 5: 验证

**Files:**
- Modify: 无

**Step 1: 运行 Web 测试**

Run: `npm --prefix apps/web test`
Expected: PASS

**Step 2: 运行 Agent 定向测试**

Run: `PYTHONPATH=apps/agent:apps/agent/tests .venv/bin/python -m unittest apps.agent.tests.test_query_log_repository_unittest apps.agent.tests.test_agent_flow_behavior_unittest -v`
Expected: PASS

**Step 3: Docker 环境端到端验证**

Run: 触发一次 `POST /chat`，再查询 `agent_query_log`
Expected: 新字段存在且写入完整结果 JSON
