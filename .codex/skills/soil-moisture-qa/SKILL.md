---
name: soil-moisture-qa
description: >
  Use when running QA, regression testing, or business review for the
  soil-moisture Agent. Single source of truth is the 56-case formal
  acceptance library at testdata/agent/soil-moisture/case-library.md.
---

# Smart Agriculture — 墒情 Agent QA Skill

> **架构版本**：LLM + Function Calling 5 节点。
> 正式测试入口为一套 **56 条** 的正式验收库。

## 权威入口

| 资产 | 路径 | 说明 |
|------|------|------|
| **正式 Case 主库（唯一入口）** | `testdata/agent/soil-moisture/case-library.md` | 56 条正式验收 Case，每次全量执行 |
| Agent 能力方案 | `apps/agent/plans/1/1.plan.md` | 5 节点 Flow、4 Tool、5 answer_type |
| Flow 风险契约 | `apps/agent/plans/1/8.flow-risk-contract.md` | 风险边界、失败路径、降级口径 |

## 发布前正式门禁（Release Gate）

> 与历史 `scripts/qa/run-soil-moisture-release-gate.sh` **等价**：先本地验活，再跑 56 条正式 Case 并写报告。以本节为唯一权威步骤（不再维护独立 `.sh`）。

### 前置条件

- 在**仓库根目录**执行；环境变量已加载（可先 `source scripts/dev/load-root-env.sh`）。
- 存在可执行 `.venv/bin/python`。
- 已配置 `HEALTH_PASSWORD`。
- 本地 Web + Agent 已启动；`BASE_WEB` 默认 `http://localhost:3000`；Agent 端口优先读 `.runtime/local-agent-port`，缺失则 `18010`。

### 门禁 1/2：本地健康冒烟

```bash
LOCAL_AGENT_PORT=$(test -f .runtime/local-agent-port && cat .runtime/local-agent-port || echo 18010)
export BASE_WEB="${BASE_WEB:-http://localhost:3000}"
export BASE_AGENT="${BASE_AGENT:-http://localhost:${LOCAL_AGENT_PORT}}"
BASE_WEB="$BASE_WEB" BASE_AGENT="$BASE_AGENT" bash scripts/health/check-local.sh
```

### 门禁 2/2：56 条正式验收（生成报告）

```bash
export FORMAL_AGENT_URL="${FORMAL_AGENT_URL:-${BASE_AGENT}/chat}"
env -u ALL_PROXY -u all_proxy -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
  FORMAL_AGENT_URL="$FORMAL_AGENT_URL" \
  .venv/bin/python testdata/agent/soil-moisture/scripts/generate_formal_acceptance_report.py
```

报告路径：`testdata/agent/soil-moisture/outputs/formal-acceptance-report.md`。

### 一键等价（npm）

仓库根目录、环境就绪时：

```bash
npm run qa:soil:formal
```

`package.json` 中 `qa:soil:formal` 内联上述两步逻辑，无需单独 shell 脚本。

## 架构约束（QA 必须对齐）

### 5 节点 Flow

`InputGuard → AgentLoop → DataFactCheck → AnswerVerify → FallbackGuard`

### 4 个业务 Tool

- `query_soil_summary`
- `query_soil_ranking`
- `query_soil_detail`
- `query_soil_comparison`（横向对比，2026 Q2 加入）

> 空结果诊断不再通过独立 Tool 调用，而是由系统在 `query_soil_*` 返回空时
> 自动产出 `answer_facts.empty_result_path`（`no_data_in_window` /
> `entity_not_found`）。

### 5 个一级 `answer_type`

- `soil_summary_answer`
- `soil_ranking_answer`
- `soil_detail_answer`
- `guidance_answer`
- `fallback_answer`

### `input_type`

- `greeting`
- `capability_question`
- `ambiguous_low_confidence`
- `business_direct`
- `business_colloquial`
- `out_of_domain`
- `conversation_closing`
- `domain_knowledge_question`（领域知识解释，不查库）

### 辅助字段

- `output_mode`: `normal / anomaly_focus / warning_mode / advice_mode`
- `guidance_reason`: `clarification / safe_hint / boundary / closing`
- `fallback_reason`: `no_data / entity_not_found / tool_missing / tool_blocked / fact_check_failed / unknown`
- `entity_confidence`: `high / medium / low`
  - `low` → `should_clarify=true`，由 ParameterResolver 拦截，**不查库**
  - `medium` → 继续查询，回答中**必须附"置信度中"说明**
  - `high` → 正常查询
- `empty_result_path`: `no_data_in_window / entity_not_found`（系统自动诊断）
- `fact_check.numeric_mismatch`: 关键数值容差 `±0.5%`，超出即触发 `fact_check_failed` 并降级

### P0 红线

业务问题必须先命中 Tool，不能让 LLM 在未查真实数据的情况下直接给业务结论。
两个对偶失败路径：
- `tool_missing`：业务问题但 `tool_trace=[]`（包含用户显式拒绝查库、LLM 跳过工具两类）
- `tool_blocked`：调用了 Tool 但执行失败（DB 不可用 / 限流 / 权限拒绝），由 `FallbackGuard` 兜底

---

## 正式验收库结构

正式库共 **56** 条，分布固定：

| 章节 | 数量 | CaseID |
|---|---:|---|
| Guidance Cases | 15 | `SM-CONV-001 ~ SM-CONV-015` |
| Summary Cases | 10 | `SM-SUM-001 ~ SM-SUM-010` |
| Ranking Cases | 8 | `SM-RANK-001 ~ SM-RANK-008` |
| Detail Cases | 13 | `SM-DETAIL-001 ~ SM-DETAIL-013` |
| Fallback Cases | 10 | `SM-FB-001 ~ SM-FB-010` |

### 必须覆盖的重点

- guidance：四类 `guidance_reason` 全覆盖（含 `domain_knowledge_question`、多轮时间切换）
  - **时间澄清**：模糊时间（CONV-003，“这几天”）/ 超范围时间（CONV-013，“最近400天”）/ 非法时间区间（CONV-014，开始时间晚于结束时间）
  - **对抗性**：prompt injection（CONV-012）
  - **上下文重置**：closing 后再开新业务（CONV-015）
- summary：普通 / 地区 / latest / anomaly / warning / advice / 最近 13 天 / 近 2 周 / 近 3 个月 / `entity_confidence=medium`
- ranking：TopN / 顺序 / 时间窗 / 维度（city/county/device）/ `top_n=10` 边界 / 最近 21 天 / `query_soil_comparison` 横向对比
- detail：地区 / 设备 / 别名 / 多轮 / anomaly / warning / advice / `entity_confidence=high`
  - **多轮深化**：3+ 轮上下文继承（DETAIL-012）/ 否定修正（DETAIL-013）
- fallback：**六类 `fallback_reason` 全覆盖** → `no_data / entity_not_found / tool_missing / tool_blocked / fact_check_failed / unknown`
  - `entity_not_found` 三种来源：SN 不存在（FB-002）/ `entity_confidence=low` 阻断（FB-005）/ 非法字符 SQL 注入风格（FB-010）
  - `tool_missing` 两种触发：显式拒绝查库（FB-003）/ LLM 自行跳过工具（FB-006）
  - `fact_check_failed` 两种类型：有数据被错答成无（FB-004）/ 数值偏差超容差（FB-007）
  - `tool_blocked`：DB 不可用 / 限流 / 权限拒绝（FB-008）
  - `unknown`：catch-all 兜底，未分类异常 / 非法 JSON / 未捕获 panic（FB-009）

---

## 正式验收要求

### 每次都全跑

正式要求是：
- 只维护一套正式库
- 每次都全量跑完 56 条
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

### 标准详细测试报告

当用户明确要求“正式测试报告”“逐条详细报告”“56 条 Case 全量验收报告”时，必须按统一报告标准输出。

推荐报告落点：

- `testdata/agent/soil-moisture/outputs/formal-acceptance-report.md`

若另存其他路径，也必须在结果中明确写出最终文件位置。

#### 报告范围

- 必须逐条覆盖全部 **56** 条正式 Case
- 不允许抽样
- 每条业务 Case 都必须包含数据库回查与事实校验
- 每条业务 Case 都必须明确给出 `是否符合事实`

#### 每条 Case 的固定报告字段

每条 Case 至少输出：

- `CaseID`
- `用户问题`
- `上下文`
- `预期 input_type`
- `预期 Tool`
- `预期 answer_type`
- `预期 output_mode`
- `预期 guidance_reason`
- `预期 fallback_reason`
- `实际 input_type`
- `实际 Tool`
- `实际 answer_type`
- `实际 output_mode`
- `实际 guidance_reason`
- `实际 fallback_reason`
- `实际 final_answer`
- `tool_trace`
- `query_result`
- `answer_facts`
- `query_log_entries`
- `执行 SQL` 或 `等效 SQL`
- `SQL 参数`
- `SQL 结果摘要`
- `SQL 结果样本`
- `当前回答（Case 样例）`
- `事实校验结果`
- `是否符合事实`
- `是否通过`
- `失败原因`
- `修复建议`

#### SQL 说明要求

- 优先记录真实执行 SQL，例如：
  - `agent_query_log.executed_sql_text`
  - 测试过程可拿到的 repository 实际 SQL
- 如果当前实现拿不到 literal SQL，则必须输出 **等效 SQL**
- 使用等效 SQL 时要明确标记：
  - `SQL 类型：等效 SQL（由查询条件重建）`

#### 事实校验要求

每条业务 Case 至少校验适用项：

- 地区是否正确
- 设备是否正确
- 时间范围是否正确
- 排名顺序是否正确
- 关键数字是否正确
- 是否真的存在异常 / 无数据 / 预警条件
- 回答是否包含数据库无法支撑的结论

如果 Case 中定义了以下字段，也必须逐项核验：

- `预期实体`
- `预期时间窗`
- `预期关键指标`
- `预期排序结果`
- `预期诊断类别`
- `必含事实`
- `禁止事实`

#### 严格失败标准

出现以下任意一项，该 Case 直接失败：

- 域内业务问题未命中 Tool
- Tool 命中错误
- `answer_type` 错误
- `output_mode / guidance_reason / fallback_reason` 错误
- 没有结构化证据
- 没有 SQL 或等效 SQL
- 没有数据库回查
- 回答中的关键数字与数据库不一致
- 回答中的地区 / 设备 / 时间范围不一致
- 排名顺序不一致
- guidance Case 误查库
- fallback Case 分类错误
- 回答出现数据库无法支撑的事实结论
- `是否符合事实=是`，但实际数据库核验失败

#### 报告结论

完整报告最后必须给出：

- 测试范围
- 正式库自检结果
- Python / Node 测试结果
- 56 条逐条测试结果
- 数据库真实性校验汇总
- 哪些 Case 的 `是否符合事实` 需要调整
- 是否仍存在“未调 Tool 直接回答业务问题”的路径
- 最终结论：
  - `通过`
  - `有条件通过`
  - `不通过`

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
