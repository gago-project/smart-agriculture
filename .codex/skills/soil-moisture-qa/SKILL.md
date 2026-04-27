---
name: soil-moisture-qa
description: >
  Use when running QA, regression testing, or business review for the
  soil-moisture Agent. Single source of truth is the 30-case formal
  acceptance library at testdata/agent/soil-moisture/case-library.md.
---

# Smart Agriculture — 墒情 Agent QA Skill

> **架构版本**：LLM + Function Calling 5 节点（已完成迁移）。
> 当前正式测试入口已废弃旧三层测试模型，只保留一套 **30 条** 的正式验收库。

## 权威入口

| 资产 | 路径 | 说明 |
|------|------|------|
| **正式 Case 主库（唯一入口）** | `testdata/agent/soil-moisture/case-library.md` | 30 条正式验收 Case，每次全量执行 |
| Agent 能力方案 | `apps/agent/plans/1/1.plan.md` | 5 节点 Flow、4 Tool、5 answer_type |
| 风险审计与整改 | `apps/agent/plans/1/9.llm-fc-design-audit.md` | 风险、契约、测试口径 |

## 架构约束（QA 必须对齐）

### 5 节点 Flow

`InputGuard → AgentLoop → DataFactCheck → AnswerVerify → FallbackGuard`

### 4 个 Tool

- `query_soil_summary`
- `query_soil_ranking`
- `query_soil_detail`
- `diagnose_empty_result`

### 5 个一级 `answer_type`

- `soil_summary_answer`
- `soil_ranking_answer`
- `soil_detail_answer`
- `guidance_answer`
- `fallback_answer`

### 辅助字段

- `output_mode`: `normal / anomaly_focus / warning_mode / advice_mode`
- `guidance_reason`: `clarification / safe_hint / boundary / closing`
- `fallback_reason`: `no_data / entity_not_found / tool_missing / tool_blocked / fact_check_failed / unknown`

### P0 红线

业务问题必须先命中 Tool，不能让 LLM 在未查真实数据的情况下直接给业务结论。

---

## 正式验收库结构

正式库共 **30** 条，分布固定：

| 一级 `answer_type` | 数量 | CaseID |
|---|---:|---|
| `guidance_answer` | 8 | `SM-CONV-001 ~ SM-CONV-008` |
| `soil_summary_answer` | 6 | `SM-SUM-001 ~ SM-SUM-006` |
| `soil_ranking_answer` | 4 | `SM-RANK-001 ~ SM-RANK-004` |
| `soil_detail_answer` | 8 | `SM-DETAIL-001 ~ SM-DETAIL-008` |
| `fallback_answer` | 4 | `SM-FB-001 ~ SM-FB-004` |

### 必须覆盖的重点

- guidance：四类 `guidance_reason` 各 2 条
- summary：普通 / 地区 / latest / anomaly / warning / advice
- ranking：TopN / 顺序 / 时间窗 / 维度
- detail：地区 / 设备 / 别名 / 多轮 / anomaly / warning / advice
- fallback：`no_data / entity_not_found / tool_missing / fact_check_failed`

---

## 正式验收要求

### 每次都全跑

旧三层测试模型已废弃。

当前正式要求是：
- 只维护一套正式库
- 每次都全量跑完 30 条
- 测试以单元测试为主

### 长文本回答必须保留

每条 Case 都必须保留完整 `当前回答` 长文本样例。

### 数据真实性是第一优先级

每条业务 Case 都必须带：
- `数据库校验断言`
- `是否符合事实`

正式通过标准：
- 业务 Case：`是否符合事实=是`
- 非业务 guidance Case：若不含事实性业务断言，也可记为 `是`

### 自动化校验原则

不要做全文精确匹配；优先校验：
- Tool 是否正确
- `answer_type / output_mode / guidance_reason / fallback_reason` 是否正确
- 结构化证据字段是否存在
- 回答中的关键事实是否被数据库支撑
- 回答中是否出现数据库无法支持的结论

---

## 什么时候必须补 Case

出现以下任一情况，必须在正式库补或改 Case：

- Tool 入参或返回结构改变
- `answer_type / output_mode / guidance_reason / fallback_reason` 契约改变
- 地区 / 设备识别逻辑改变
- 修复了可稳定复现的线上问题
- 数据真实性校验规则改变

---

## 商务评审使用方式

给商务或产品同事使用时，只让他们看：
- 用户问题
- 当前回答
- 是否符合预期
- 备注

不要要求他们关注：
- Tool 名称
- 内部路由
- 结构化证据字段

商务评审反馈分两类：
- **表达优化**：回写 `当前回答`
- **能力缺口 / 事实错误**：回写正式库与实现逻辑
